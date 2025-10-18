from langsmith import traceable
from langgraph.prebuilt import create_react_agent
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.callbacks.base import BaseCallbackHandler
from langchain_openai import ChatOpenAI
from langchain_experimental.agents.agent_toolkits.pandas.base import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI as PandasChatOpenAI
from typing import List, Optional, Dict, Any
from bson import ObjectId

import pandas as pd
import logging
import traceback
import tempfile
import os

from api.embed import similarity, embed_question
from api.schemas.agents import convert_messages_to_dict
from api.database import agents_db, connectors_db, knowledge_db, minio_client

class TokenCountingCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.reset()

    def reset(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def on_llm_end(self, response, **kwargs):
        usage = getattr(response, "llm_output", {}).get("token_usage", {})
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.completion_tokens += usage.get("completion_tokens", 0)
        self.total_tokens += usage.get("total_tokens", 0)


class LoggingChatOpenAI(ChatOpenAI):
    async def agenerate(self, messages, *args, **kwargs):
        return await super().agenerate(messages, *args, **kwargs)

    def generate(self, messages, *args, **kwargs):
        return super().generate(messages, *args, **kwargs)

def _clean_tool_name(name: str, prefix: str) -> Dict[str, str]:
    import re, unidecode
    name_ascii = unidecode.unidecode(name)
    sanitized = re.sub(r'[^a-zA-Z0-9_-]+', '_', name_ascii)
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_')
    tool_name = f"{prefix}_{sanitized}".lower()
    llm_label = name.strip()
    return {"tool_name": tool_name, "llm_label": llm_label}

def retrieve_relevant_context(
    question: str | list,
    context_docs: List[Dict[str, Any]],
    top_n: int = 3,
    top_rows: int = 10,
) -> str:
    """
    Retrieve the most relevant context from a list of context_docs for the given question.
    For text documents: uses embedding similarity to select top-n chunks (unchanged).
    For tabular CSV/Excel documents: reconstructs DataFrame and uses a Pandas agent to generate context.
    The result merges tabular agent outputs with the text-based top-n chunks.
    """

    if not context_docs or not question:
        return "⚠️ No relevant context found for this question."

    question_text = question if isinstance(question, str) else " ".join(question)
    try:
        question_emb = embed_question(question_text)
    except Exception:
        return "⚠️ No relevant context found for this question."

    tabular_context_outputs = []
    tabular_file_keys = set()
    text_chunks_scored = []

    for idx, doc in enumerate(context_docs):
        try:
            doc_is_tabular = doc.get("is_tabular", False)
            file_key = doc.get("file_key", None)
            if doc_is_tabular and file_key:
                tabular_file_keys.add(file_key)
                continue

            if "chunks" in doc and isinstance(doc["chunks"], list):
                for chunk in doc["chunks"]:
                    chunk_text = chunk.get("text", "")
                    if not chunk_text.strip():
                        continue
                    try:
                        chunk_emb = chunk.get("embedding") or embed_question(chunk_text[:2000])
                        sim = similarity(question_emb, chunk_emb)
                        text_chunks_scored.append((sim, chunk_text))
                    except Exception:
                        pass
            elif doc.get("text"):
                chunk_text = doc["text"]
                try:
                    chunk_emb = doc.get("embedding") or embed_question(chunk_text[:2000])
                    sim = similarity(question_emb, chunk_emb)
                    text_chunks_scored.append((sim, chunk_text))
                except Exception:
                    pass
        except Exception:
            pass

    for file_key in tabular_file_keys:
        tabular_docs = [doc for doc in context_docs if doc.get("file_key") == file_key and doc.get("is_tabular", False)]
        df = None
        filename = "_".join(file_key.split("_")[1:]) if file_key else "unknown"
        data_json = None
        for doc in tabular_docs:
            if "data_json" in doc and doc["data_json"]:
                data_json = doc["data_json"]
                break
        if data_json:
            try:
                df = pd.read_json(data_json, orient="split")
            except Exception:
                df = None
        if df is None and tabular_docs:
            rows = []
            header = None
            for doc in tabular_docs:
                if "row" in doc and isinstance(doc["row"], dict):
                    rows.append(doc["row"])
                elif "text" in doc and doc["text"]:
                    try:
                        if not header and "metadata" in doc and "header" in doc["metadata"]:
                            header = doc["metadata"]["header"]
                        if header:
                            values = [v.strip() for v in doc["text"].split(",")]
                            row_dict = dict(zip(header, values))
                            rows.append(row_dict)
                    except Exception:
                        pass
            if rows:
                try:
                    df = pd.DataFrame(rows)
                except Exception:
                    df = None
        if df is not None and not df.empty:
            try:
                # Use Pandas agent to answer the question about the DataFrame
                # Use a small, low-cost model for table analysis
                pandas_llm = PandasChatOpenAI(model="gpt-3.5-turbo", temperature=0)
                pandas_agent = create_pandas_dataframe_agent(pandas_llm, df, verbose=False)
                tabular_prompt = (
                    f"The following table is from '{filename}'. "
                    f"Given the user's question, answer using only this table's data. "
                    f"User's question: {question_text}"
                )
                agent_response = pandas_agent.invoke(tabular_prompt)
                # Compose result
                tabular_context_outputs.append(f"📊 Table context from '{filename}':\n{agent_response}")
            except Exception:
                logging.error(f"Failed to process tabular data for file_key {file_key}:\n{traceback.format_exc()}")

    selected_contexts = []
    if text_chunks_scored:
        text_chunks_scored.sort(reverse=True, key=lambda x: x[0])
        top_text_chunks = text_chunks_scored[:top_n]
        for sim, text in top_text_chunks:
            selected_contexts.append(text)

    if tabular_context_outputs:
        selected_contexts.extend(tabular_context_outputs)

    if not selected_contexts:
        return "⚠️ No relevant context found for this question."

    final_context = "\n\n".join(selected_contexts)
    return final_context

@traceable
async def get_agent_graph(
    question: str,
    organization_id: ObjectId,
    chat_history: Optional[List[dict]] = None,
    agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Returns a dict with:
    - graph: the React agent graph or fallback LLM
    - messages: the chat history in dict form
    - final_agent_name: the agent's name
    - final_agent_id: the agent's id (str) or None
    """
    question = question.strip()
    chat_history = chat_history or []
    selected_agent = None

    if agent_id:
        if agent_id == "auto":
            agents = list(agents_db.find({"org": organization_id}))
            if agents:
                agent_descriptions = "\n".join([f"- **{agent['name']}**: {agent['description']}" for agent in agents])
                router_prompt = [
                    SystemMessage(
                        content=(
                            "You are an expert at routing a user's request to the correct agent. "
                            "Based on the user's question, select the best agent from the following list. "
                            "You must output **only the name** of the agent you choose. "
                            "If no agent seems suitable, output 'Generalist'."
                            f"\n\nAvailable Agents:\n{agent_descriptions}"
                        )
                    ),
                    HumanMessage(content=question),
                ]
                router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
                selected_agent_name_response = await router_llm.ainvoke(router_prompt)
                selected_agent_name = selected_agent_name_response.content.strip()
                selected_agent = next((agent for agent in agents if agent["name"] == selected_agent_name), None)
        elif agent_id == "generalist":
            selected_agent = None
        else:
            selected_agent = agents_db.find_one({"_id": ObjectId(agent_id), "org": organization_id})
    else:
        selected_agent = None

    active_tools = []

    async def get_search_web_tool():
        from api.tools.web import get_search_web_tool
        return get_search_web_tool()

    builtin_tool_factories = {"search_web": get_search_web_tool}
    connector_tool_factory_map = {
        "google_sheet": "api.tools.google_sheet.get_google_sheet_tool",
        "google_drive": "api.tools.google_drive.get_google_drive_tool",
        "source_pdf": "api.tools.pdf_source.get_pdf_source_tool",
        "source_uri": "api.tools.uri_source.get_uri_source_tool"
    }

    if selected_agent:
        import importlib
        for tool_name in selected_agent.get("tools", []):
            factory = builtin_tool_factories.get(tool_name)
            if factory:
                active_tools.append(await factory())

        connector_ids = selected_agent.get("connector_ids", [])
        if connector_ids:
            agent_connectors = list(connectors_db.find({"_id": {"$in": connector_ids}}))
            for connector in agent_connectors:
                try:
                    connector_type = connector.get("connector_type")
                    tool_factory_path = connector_tool_factory_map.get(connector_type)
                    if not tool_factory_path:
                        continue
                    module_path, func_name = tool_factory_path.rsplit(".", 1)
                    tool_factory = getattr(importlib.import_module(module_path), func_name)
                    names = _clean_tool_name(connector["name"], connector_type)
                    tool_name = names["tool_name"]
                    llm_label = names["llm_label"]

                    if connector_type in ["source_pdf", "source_uri"]:
                        active_tools.append(tool_factory(settings=connector["settings"], name=tool_name))
                    else:
                        active_tools.append(tool_factory(settings=connector["settings"], name=tool_name, llm_label=llm_label))
                except Exception:
                    pass

        for tool in active_tools:
            if hasattr(tool, "run"):
                original_run = tool.run
                if callable(original_run):
                    async def logging_run(input_text, original_run=original_run, tool=tool):
                        output = await original_run(input_text)
                        return output
                    tool.run = logging_run

        available_sources = []
        for tool in active_tools:
            tool_name = getattr(tool, 'name', 'unknown')
            llm_label = getattr(tool, 'llm_label', tool_name)
            description = getattr(tool, 'description', 'No description provided.')
            available_sources.append(f"- {llm_label}: {description}")
        connectors_text = "\n".join(available_sources)

        context_ids = selected_agent.get("context", [])

        context_docs = []
        context_text = ""
        for context_entry_id in context_ids:
            entry_doc = knowledge_db.find_one({"_id": ObjectId(context_entry_id)})
            if not entry_doc:
                continue

            filename = "_".join(entry_doc.get("file_key", "").split("_")[1:]) if entry_doc.get("file_key") else ""

            if entry_doc.get("is_tabular", False):
                entry_exp = "The data is structured as a tabular CSV DataFrame. Use the provided data to answer questions accurately.\n"
                file_key = entry_doc.get("file_key")
                data_json = entry_doc.get("data_json")
                if data_json and file_key:
                    try:
                        df = pd.read_json(data_json, orient="split")
                        tmp_csv_path = f"/tmp/{file_key}.csv"
                        df.to_csv(tmp_csv_path, index=False)
                        loader = CSVLoader(file_path=tmp_csv_path)
                        csv_docs = loader.load()
                        context_docs.extend(csv_docs)
                    except Exception as e:
                        pass
            else:
                entry_exp = "The data is text, it is likely a document that you have access to. Use the provided context from the file to answer question accordingly.\n"
                if "chunks" in entry_doc:
                    context_docs.extend(entry_doc["chunks"])
                elif "text" in entry_doc:
                    context_docs.append(entry_doc)

            context_text += f"📄 Document: '{filename}'\n{entry_doc.get('text', '')}\n{entry_exp}\n"

        relevant_context = retrieve_relevant_context(question, context_docs)

        system_prompt = f"""
            You are an AI agent built by user in Nexa AI platform. Nexa AI is a platform for building AI agents with specialized tools and connectors for organizations to use.
            You are now operating as the agent named **{selected_agent['name']}**.
            Here's the description user provided for the said agent: {selected_agent.get("description") or "No description provided."}

            You have a context window of relevant information retrieved from the organization's knowledge base.
            Use this information to help you answer user questions. If the context does not contain the information you need first.
            This is the context you have access to:
            {context_text}

            Relevant context retrieved for this specific question from the context you have:
            {relevant_context}

            Only use the Relevant context above to answer question regarding the knowledge base.
            You must not invent any data. Only report values present in the retrieved tabular rows or text chunks. If the answer is not present, explicitly state that the knowledge base does not contain the information.
            If the relevant context does not contain the information you need, you can use your own knowledge and reasoning to answer the question BUT explictly tell the user that the answer is not based on the organization's knowledge base.

            You also have access to specialized tools and connectors to help you find information and perform actions.
            Here are the available tools and connectors you can use:
            {connectors_text}

            When the information you need is not in the context, you can use the specialized connectors available to you.
            If you need to use a connector, decide which tool is most appropriate for the task and use it.
            If you need to use a connector multiple times, you can do so.
            You have access to the following connectors: {', '.join([getattr(t, 'llm_label', getattr(t, 'name', 'unknown')) for t in active_tools])}.

            Then if the info you need is not available in the context or via connectors, you can use your own knowledge and reasoning to answer the question.

            Also, User's Organization ID is {organization_id}.
        """

        messages_list = [SystemMessage(content=system_prompt)]
        for entry in chat_history:
            user_text = entry.get("user", "").strip()
            assistant_text = entry.get("assistant", "").strip()
            if user_text:
                messages_list.append(HumanMessage(content=user_text))
            if assistant_text:
                messages_list.append(AIMessage(content=assistant_text))
        messages_list.append(HumanMessage(content=question))

        final_agent_id = selected_agent["_id"]
        final_agent_name = selected_agent["name"]
        agent_llm = LoggingChatOpenAI(
            model=selected_agent["model"],
            temperature=selected_agent.get("temperature", 0.7),
            streaming=True,
            max_retries=3,
        )
        graph = create_react_agent(agent_llm, active_tools)
        setattr(graph, "_is_react_agent", True)
        graph.system_prompt = system_prompt

        messages_dict = convert_messages_to_dict(messages_list)

        def _count_words(text):
            return len(text.split())
        prompt_tokens = sum(_count_words(m.get("content", "")) for m in messages_dict if m.get("role") in ("system","user","assistant","human"))
        completion_tokens = 0
        total_tokens = prompt_tokens + completion_tokens
        token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }
        return {
            "graph": graph,
            "messages": messages_dict,
            "final_agent_name": final_agent_name,
            "final_agent_id": str(final_agent_id) if final_agent_id else None,
            "token_usage": token_usage
        }
    else:
        # Remove streaming token handler logic, instead count tokens after composing prompt and completion
        agent_llm = LoggingChatOpenAI(
            model="gpt-4o-mini",
            streaming=True,
            temperature=0.7,
            max_retries=3,
        )
        graph = create_react_agent(agent_llm, tools=[])
        setattr(graph, "_is_react_agent", True)
        system_prompt = f"""
            You are an AI agent called Generalist in Nexa AI platform. Nexa AI is a platform for building AI agents with specialized tools and connectors for organizations to use.
            You do not have access to any specialized tools or connectors. You are a general-purpose fallback assistant that can help with a wide range of topics. You are called when no other specialized agents are available.
            Use your own knowledge and reasoning to answer the user's question to the best of your ability.
            And try to be resistant to answering questions that are too specific to the organization's knowledge base or require specialized tools and tell them that they need to create an AI agent in Nexa AI and create their own connectors, upload their own documents to get used as agent's knowledge base.
            As you are a fallback agent, You should act more like an advertiser of what Nexa AI platform can do and how users can create their own agents with specialized tools and connectors to help them with their specific needs.
            Here's an example of how they can create their own agent in Nexa AI platform:
            1. In the dashboard, go to the "Agents" section and click on "Create Agent".
            2. Provide a name and persona for your agent.
            3. Select the tools and connectors you want your agent to have access to.
            4. Upload documents to the knowledge base that your agent can use to answer questions.
            5. Save your agent and start using it to answer questions.
            
            If you cannot answer a question, suggest that the user create their own agent in Nexa AI platform.
            Always remember to promote the capabilities of Nexa AI platform and how users can create their own agents with specialized tools and connectors to help them with their specific needs.

            Also, User's Organization ID is {organization_id}.
        """
        graph.system_prompt = system_prompt

        messages_list = [SystemMessage(content=system_prompt)]
        for entry in chat_history:
            user_text = entry.get("user", "").strip()
            assistant_text = entry.get("assistant", "").strip()
            if user_text:
                messages_list.append(HumanMessage(content=user_text))
            if assistant_text:
                messages_list.append(AIMessage(content=assistant_text))
        messages_list.append(HumanMessage(content=question))

        messages_dict = convert_messages_to_dict(messages_list)

        def _count_words(text):
            return len(text.split())
        prompt_tokens = sum(_count_words(m.get("content", "")) for m in messages_dict if m.get("role") in ("system","user","assistant","human"))
        completion_tokens = 0
        total_tokens = prompt_tokens + completion_tokens
        token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }

        return {
            "graph": graph,
            "messages": messages_dict,
            "final_agent_name": "Generalist",
            "final_agent_id": None,
            "token_usage": token_usage
        }
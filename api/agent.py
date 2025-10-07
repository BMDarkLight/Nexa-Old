from langchain_openai import ChatOpenAI
from langsmith import traceable
from langgraph.prebuilt import create_react_agent
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from typing import List, Optional, Dict, Any
from bson import ObjectId

import re
import importlib
import logging
import unidecode
import pandas as pd

from api.embed import similarity, embed_question
from api.schemas.agents import convert_messages_to_dict
from api.database import agents_db, connectors_db, knowledge_db


def retrieve_relevant_context(question: str | list, context_docs: List[Dict[str, Any]], top_n: int = 3) -> str:
    if not context_docs or not question:
        return ""

    question_text = question if isinstance(question, str) else " ".join(question)
    try:
        question_emb = embed_question(question_text)
    except Exception as e:
        logging.error(f"Failed to embed question: {e}")
        return ""

    scored_docs = []

    for idx, doc in enumerate(context_docs):
        try:
            if doc.get("is_tabular"):
                structured_data = doc.get("structured_data", {})
                if not structured_data:
                    continue

                df = pd.DataFrame(structured_data.get("sample", []))
                if df.empty:
                    continue

                table_text = df.head(10).to_string(index=False)
                table_emb = embed_question(table_text)
                score = similarity(question_emb, table_emb)

                keywords = re.findall(r'\b[A-Za-z0-9_]+\b', question_text.lower())
                matching_columns = [col for col in df.columns if any(k in col.lower() for k in keywords)]

                if matching_columns:
                    filtered_df = df[df[matching_columns].apply(lambda row: any(
                        str(v).lower() in question_text.lower() for v in row.values
                    ), axis=1)]
                else:
                    filtered_df = df.head(5)

                preview_rows = min(10, len(filtered_df))
                filtered_preview = filtered_df.head(preview_rows).to_string(index=False)

                filename = "_".join(doc.get("file_key", "").split("_")[1:]) if doc.get("file_key") else "unknown"

                context_text = (
                    f"📊 Relevant data from '{filename}':\n"
                    f"{filtered_preview}\n\n"
                    f"Columns: {', '.join(df.columns[:8])}"
                )

                scored_docs.append((score, {"text": context_text}))
                continue

            text_chunks = [chunk.get("text", "") for chunk in doc.get("chunks", [])]
            combined_text = "\n".join(text_chunks)
            if not combined_text.strip():
                continue

            doc_emb = doc.get("embedding")
            if not doc_emb:
                doc_emb = embed_question(combined_text[:2000])

            score = similarity(question_emb, doc_emb)
            scored_docs.append((score, {"text": combined_text}))

        except Exception as e:
            logging.error(f"Error processing document #{idx}: {e}")

    if not scored_docs:
        return ""

    scored_docs.sort(reverse=True, key=lambda x: x[0])
    top_docs = [doc for _, doc in scored_docs[:top_n]]
    final_context = "\n\n".join(doc.get("text", "") for doc in top_docs if doc.get("text"))
    logging.info(f"Returning {len(top_docs)} context entries (including tabular retrieval).")

    return final_context

def _clean_tool_name(name: str, prefix: str) -> Dict[str, str]:
    name_ascii = unidecode.unidecode(name)
    sanitized = re.sub(r'[^a-zA-Z0-9_-]+', '_', name_ascii)
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_')
    tool_name = f"{prefix}_{sanitized}".lower()
    llm_label = name.strip()
    return {"tool_name": tool_name, "llm_label": llm_label}

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
        selected_agent = agents_db.find_one({"_id": ObjectId(agent_id), "org": organization_id})
    elif agent_id == "auto":
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
                        logging.warning(f"No tool factory defined for connector type: {connector_type}")
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

                    logging.info(f"Loaded connector tool: {tool_name}")
                except Exception as e:
                    logging.error(f"Failed to create tool for connector {connector.get('name')}: {e}")

        logging.info(f"Active tools for agent '{selected_agent['name'] if selected_agent else 'Generalist'}': "
                     f"{[(getattr(t, 'name', None), getattr(t, 'llm_label', None)) for t in active_tools]}")

        for tool in active_tools:
            if hasattr(tool, "run"):
                original_run = tool.run
                if callable(original_run):
                    async def logging_run(input_text, original_run=original_run, tool=tool):
                        logging.info(f"Tool '{getattr(tool, 'name', 'unknown')}' called with input: {input_text}")
                        output = await original_run(input_text)
                        logging.info(f"Tool '{getattr(tool, 'name', 'unknown')}' output: {output}")
                        return output
                    tool.run = logging_run

        context_ids = selected_agent.get("context", [])

        context_docs = []
        for context_entry_id in context_ids:
            entry_doc = knowledge_db.find_one({"_id": ObjectId(context_entry_id)})
            if entry_doc and "chunks" in entry_doc:
                context_docs.extend(entry_doc["chunks"])

        relevant_context = retrieve_relevant_context(question, context_docs)

        system_prompt = f"""
            You are an AI agent built by user in Nexa AI platform. Nexa AI is a platform for building AI agents with specialized tools and connectors for organizations to use.
            You are now operating as the agent named **{selected_agent['name']}**.
            Here's the description user provided for the said agent: {selected_agent.get("description") or "No description provided."}

            You have a context window of relevant information retrieved from the organization's knowledge base.
            Use this information to help you answer user questions. If the context does not contain the information you need first.
            Relevant context retrieved from organization's knowledge base:
            {relevant_context}

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
        agent_llm = ChatOpenAI(model=selected_agent["model"], temperature=selected_agent.get("temperature", 0.7), streaming=True, max_retries=3)
        graph = create_react_agent(agent_llm, active_tools)
        setattr(graph, "_is_react_agent", True)
        graph.system_prompt = system_prompt

        messages_dict = convert_messages_to_dict(messages_list)

        return {
            "graph": graph,
            "messages": messages_dict,
            "final_agent_name": final_agent_name,
            "final_agent_id": str(final_agent_id) if final_agent_id else None,
        }
    else:
        agent_llm = ChatOpenAI(model="gpt-4o-mini", streaming=True, temperature=0.7, max_retries=3)
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

        return {
            "graph": graph,
            "messages": messages_dict,
            "final_agent_name": "Generalist",
            "final_agent_id": None,
        }
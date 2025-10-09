from langsmith import traceable
from langgraph.prebuilt import create_react_agent
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.callbacks.manager import CallbackManager
from langchain_openai import ChatOpenAI
from typing import List, Optional, Dict, Any
from bson import ObjectId

import re
import io
import string
import importlib
import logging
import unidecode
import pandas as pd

from api.embed import similarity, embed_question
from api.schemas.agents import convert_messages_to_dict, TokenCountingCallbackHandler
from api.database import agents_db, connectors_db, knowledge_db, minio_client


class LoggingChatOpenAI(ChatOpenAI):
    async def agenerate(self, messages, *args, **kwargs):
        return await super().agenerate(messages, *args, **kwargs)

    def generate(self, messages, *args, **kwargs):
        return super().generate(messages, *args, **kwargs)

def _normalize_text(text):
    text = str(text).lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = text.strip()
    return text

def _split_to_norm_words(s):
    s = _normalize_text(s)
    return set(re.split(r"\s+", s))

def _clean_tool_name(name: str, prefix: str) -> Dict[str, str]:
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
    Handles both tabular and text document chunks. Returns a string of relevant context.
    """
    import traceback
    if not context_docs or not question:
        logging.warning("No context docs or question provided to retrieve_relevant_context.")
        return "⚠️ No relevant context found for this question."

    question_text = question if isinstance(question, str) else " ".join(question)
    try:
        question_emb = embed_question(question_text)
        logging.info("Successfully embedded the question.")
    except Exception as e:
        logging.error(f"Failed to embed question: {e}\n{traceback.format_exc()}")
        return "⚠️ No relevant context found for this question."

    tabular_rows_scored = []
    text_chunks_scored = []

    for idx, doc in enumerate(context_docs):
        try:
            doc_is_tabular = doc.get("is_tabular", False)
            file_key = doc.get("file_key", None)
            logging.debug(f"[Doc #{idx}] file_key: {file_key} | is_tabular: {doc_is_tabular}")
            if doc_is_tabular:
                if not file_key:
                    logging.warning(f"Tabular doc #{idx} missing file_key.")
                    continue
                logging.info(f"Processing tabular file: {file_key}")
                try:
                    obj = minio_client.get_object(bucket_name="context-files", object_name=file_key)
                    file_bytes = obj.read()
                    logging.info(f"Successfully read file {file_key} from MinIO.")
                except Exception as e:
                    logging.error(f"Failed to load tabular file {file_key}: {e}\n{traceback.format_exc()}")
                    continue

                rows_as_text = []
                rows_as_columns = []
                try:
                    if file_key.lower().endswith(".csv"):
                        df_iter = pd.read_csv(io.BytesIO(file_bytes), chunksize=1000)
                        for chunk in df_iter:
                            for _, row in chunk.iterrows():
                                row_strs = []
                                row_cols = []
                                for col, val in row.items():
                                    col_val_str = f"{col}: {val}"
                                    row_strs.append(col_val_str)
                                    row_cols.append((col, val, col_val_str))
                                rows_as_text.append(" | ".join(row_strs))
                                rows_as_columns.append(row_cols)
                        logging.info(f"Extracted {len(rows_as_text)} rows from CSV {file_key}.")
                    elif file_key.lower().endswith((".xls", ".xlsx")):
                        df = pd.read_excel(io.BytesIO(file_bytes))
                        for _, row in df.iterrows():
                            row_strs = []
                            row_cols = []
                            for col, val in row.items():
                                col_val_str = f"{col}: {val}"
                                row_strs.append(col_val_str)
                                row_cols.append((col, val, col_val_str))
                            rows_as_text.append(" | ".join(row_strs))
                            rows_as_columns.append(row_cols)
                        logging.info(f"Extracted {len(rows_as_text)} rows from Excel {file_key}.")
                    else:
                        logging.warning(f"Unknown tabular file format for {file_key}. Skipping.")
                        continue
                except Exception as e:
                    logging.error(f"Failed to parse tabular file {file_key}: {e}\n{traceback.format_exc()}")
                    continue

                row_similarities = []
                norm_question = _normalize_text(question_text)
                
                question_norm_words = _split_to_norm_words(question_text)
                exact_match_rows = set()
                for row_idx, (row_text, row_cols) in enumerate(zip(rows_as_text, rows_as_columns)):
                    try:
                        max_col_sim = None
                        max_col_val = None
                        col_sim_details = []
                        row_exact_match = False
                        for col, val, col_val_str in row_cols:
                            norm_col_val = _normalize_text(val)
                            boost = 0.0
                            if norm_col_val and norm_col_val in question_norm_words:
                                boost = 0.5
                                row_exact_match = True
                            elif norm_col_val and norm_col_val in norm_question:
                                boost = 0.2
                            col_emb = embed_question(col_val_str)
                            sim = similarity(question_emb, col_emb)
                            sim += boost
                            col_sim_details.append((sim, col_val_str, boost))
                            if max_col_sim is None or sim > max_col_sim:
                                max_col_sim = sim
                                max_col_val = col_val_str
                        if row_exact_match:
                            exact_match_rows.add(row_idx)
                        row_similarities.append((max_col_sim, row_text, row_exact_match))
                        logging.debug(f"[Tabular] file_key={file_key} row_idx={row_idx} max_col_sim={max_col_sim:.4f} | max_col_val={max_col_val} | col_sim_details={col_sim_details} | exact_match={row_exact_match}")
                        if row_idx % 100 == 0:
                            logging.debug(f"Processed {row_idx+1}/{len(rows_as_text)} rows for {file_key}.")
                    except Exception as e:
                        logging.error(f"Embedding/similarity error for row {row_idx} in {file_key}: {e}")
                if not row_similarities:
                    logging.info(f"No rows found or embedded for tabular file {file_key}.")
                    continue

                row_similarities.sort(reverse=True, key=lambda x: x[0])
                top_rows_actual = row_similarities[:top_rows]
                filename = "_".join(file_key.split("_")[1:]) if file_key else "unknown"
                context_text = f"📊 Top relevant rows from '{filename}':\n" + "\n".join(row for _, row, _ in top_rows_actual)

                for sim, row, is_exact in top_rows_actual:
                    if is_exact:
                        logging.info(f"Tabular retrieval [EXACT MATCH]: file={file_key} row='{row}'")

                max_score = top_rows_actual[0][0] if top_rows_actual else 0
                tabular_rows_scored.append((max_score, context_text))
                logging.info(f"Selected {len(top_rows_actual)} top rows from tabular file {file_key}.")
                continue
            
            if "chunks" in doc and isinstance(doc["chunks"], list):
                num_chunks = len(doc["chunks"])
                logging.debug(f"[Doc #{idx}] has {num_chunks} text chunks.")
                for cidx, chunk in enumerate(doc["chunks"]):
                    chunk_text = chunk.get("text", "")
                    if not chunk_text.strip():
                        logging.debug(f"Empty chunk text at doc {idx} chunk {cidx}. Skipping.")
                        continue
                    try:
                        chunk_emb = chunk.get("embedding") or embed_question(chunk_text[:2000])
                        sim = similarity(question_emb, chunk_emb)
                        text_chunks_scored.append((sim, chunk_text))
                        logging.debug(f"[Text Chunk] doc_idx={idx} chunk_idx={cidx} similarity={sim:.4f}")
                    except Exception as e:
                        logging.error(f"Text chunk embedding/similarity error at doc {idx} chunk {cidx}: {e}")
            elif doc.get("text"):
                chunk_text = doc["text"]
                logging.debug(f"[Doc #{idx}] single text chunk present.")
                try:
                    chunk_emb = doc.get("embedding") or embed_question(chunk_text[:2000])
                    sim = similarity(question_emb, chunk_emb)
                    text_chunks_scored.append((sim, chunk_text))
                    logging.debug(f"[Text Chunk] doc_idx={idx} similarity={sim:.4f}")
                except Exception as e:
                    logging.error(f"Text doc embedding/similarity error at doc {idx}: {e}")
            else:
                logging.debug(f"Doc {idx} has no text or chunks. Skipping.")
        except Exception as e:
            logging.error(f"Error processing document #{idx}: {e}\n{traceback.format_exc()}")

    selected_contexts = []
    num_text_chunks_selected = 0
    num_tabular_groups_selected = 0

    if text_chunks_scored:
        text_chunks_scored.sort(reverse=True, key=lambda x: x[0])
        top_text_chunks = text_chunks_scored[:top_n]
        for sim, text in top_text_chunks:
            selected_contexts.append(text)
        num_text_chunks_selected = len(top_text_chunks)
        logging.info(f"Selected {num_text_chunks_selected} top text chunks.")

    if tabular_rows_scored:
        tabular_rows_scored.sort(reverse=True, key=lambda x: x[0])
        for score, tabular_text in tabular_rows_scored[:top_n]:
            selected_contexts.append(tabular_text)
        num_tabular_groups_selected = min(top_n, len(tabular_rows_scored))
        logging.info(f"Selected {num_tabular_groups_selected} top tabular row groups.")

    if not selected_contexts:
        logging.warning("No relevant context found for the question after processing.")
        return "⚠️ No relevant context found for this question."

    final_context = "\n\n".join(selected_contexts)
    logging.info(f"Returning {len(selected_contexts)} context entries (text and/or tabular): "
                 f"text_chunks={num_text_chunks_selected}, tabular_groups={num_tabular_groups_selected}")
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
            filename = "_".join(entry_doc.get("file_key", "").split("_")[1:]) if entry_doc.get("file_key") else ""
            if entry_doc.get("is_tabular", False):
                entry_exp = "The data is structured an tabular, Use the provided rows to answer questions accurately.\n"
            else:
                entry_exp = "The data is text, it is likely a document that you have access to, َUse the provided context from the file to answer question accordingly.\n"
            
            context_text += f"📄 Document: '{filename}'\n{entry_doc.get('text', '')}\n{entry_exp}\n"
            if entry_doc and "chunks" in entry_doc:
                context_docs.extend(entry_doc["chunks"])

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
        callback_manager = CallbackManager([TokenCountingCallbackHandler()])
        agent_llm = LoggingChatOpenAI(
            model=selected_agent["model"],
            temperature=selected_agent.get("temperature", 0.7),
            streaming=True,
            max_retries=3,
            callback_manager=callback_manager
        )
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
        callback_manager = CallbackManager([TokenCountingCallbackHandler()])
        agent_llm = LoggingChatOpenAI(
            model="gpt-4o-mini",
            streaming=True,
            temperature=0.7,
            max_retries=3,
            callback_manager=callback_manager
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

        return {
            "graph": graph,
            "messages": messages_dict,
            "final_agent_name": "Generalist",
            "final_agent_id": None,
        }
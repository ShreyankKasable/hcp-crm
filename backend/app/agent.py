"""LangGraph agent: StateGraph + ReAct loop + checkpointer, and the runner.

The runner (`run_agent`) invokes the graph for one user turn, then pulls the
form_patch out of the tool result(s) produced this turn so the API can send it
to the frontend alongside the assistant's text.
"""
import json
import os
from typing import TypedDict, Annotated, Optional

from langchain_core.messages import (
    BaseMessage, HumanMessage, SystemMessage, ToolMessage,
)
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from .llm import llm
from .tools import ALL_TOOLS, set_active_session


# ---- state ----

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


llm_with_tools = llm.bind_tools(ALL_TOOLS)


SYSTEM_PROMPT = """You are the AI assistant for a pharmaceutical CRM. You help a \
field representative log and manage interactions with Healthcare Professionals \
(HCPs) by controlling a form on their screen.

You MUST use the tools for all data actions. Never invent field values in prose.

Tool guide:
- log_interaction: when the rep describes a NEW meeting/call/visit to record.
- edit_interaction: when the rep corrects or changes the current interaction.
- search_hcp: when the rep asks who an HCP is or about past interactions.
- suggest_followups: when the rep asks for follow-up ideas or accepts your offer.
- search_materials: when the rep wants to find/attach a brochure or sample.

Rules:
- If the description is too vague to identify an HCP or interaction, ask ONE
  short clarifying question instead of guessing or inventing details.
- After logging, briefly confirm what was captured and offer to suggest follow-ups.
- Never mention tool names to the user. Keep replies concise and professional.
"""


def call_model(state: AgentState):
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


# ---- graph construction ----

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(ALL_TOOLS))
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", tools_condition)
workflow.add_edge("tools", "agent")

checkpointer = MemorySaver()
app_graph = workflow.compile(checkpointer=checkpointer)


# ---- runner ----

def _extract_tool_output(messages, since_index: int):
    """Scan messages produced this turn for ToolMessages, and merge their
    form_patch payloads. Returns (merged_patch, last_interaction_id)."""
    merged_patch = {}
    interaction_id = None
    for m in messages[since_index:]:
        if isinstance(m, ToolMessage):
            try:
                payload = json.loads(m.content) if isinstance(m.content, str) else m.content
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(payload, dict):
                merged_patch.update(payload.get("form_patch", {}) or {})
                eff = payload.get("db_effect", {}) or {}
                interaction_id = (
                    eff.get("created_interaction_id")
                    or eff.get("updated_interaction_id")
                    or interaction_id
                )
    return merged_patch, interaction_id


def run_agent(session_id: str, user_message: str) -> dict:
    """Run one turn. Returns { assistant_text, form_patch, interaction_id }."""
    set_active_session(session_id)

    config = {"configurable": {"thread_id": session_id}}

    # optional Langfuse tracing (enabled only if keys are present)
    # optional Langfuse tracing (enabled only if keys are present)
    langfuse_client = None
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        from langfuse import get_client
        from langfuse.langchain import CallbackHandler
        config["callbacks"] = [CallbackHandler()]
        config["metadata"] = {"langfuse_session_id": session_id}
        langfuse_client = get_client()

    # figure out where this turn's new messages will start
    try:
        prior = app_graph.get_state(config)
        start_index = len(prior.values.get("messages", [])) if prior.values else 0
    except Exception:
        start_index = 0

    result = app_graph.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config=config,
    )
    messages = result["messages"]
    form_patch, interaction_id = _extract_tool_output(messages, start_index)

    assistant_text = ""
    for m in reversed(messages):
        if m.__class__.__name__ == "AIMessage" and getattr(m, "content", ""):
            assistant_text = m.content
            break

    return {
        "assistant_text": assistant_text or "Done.",
        "form_patch": form_patch,
        "interaction_id": interaction_id,
    }
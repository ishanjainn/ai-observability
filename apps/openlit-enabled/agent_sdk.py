"""Research agent built on the OpenAI Agents SDK.

OpenLIT auto-instruments the Agents SDK (it monkeypatches ``Agent`` / ``Runner``),
so every agent run, LLM call and tool call becomes an OTel span — without changing
this code. That is the whole point of the :8081 app: SDK-level agent observability,
in contrast to the :8080 app which is observed purely by eBPF (OBI).
"""

from __future__ import annotations

import os
from typing import Any

from agents import Agent, Runner, function_tool

# NOTE: do NOT call set_tracing_disabled(True). OpenLIT instruments the Agents SDK
# through its *native* tracing pipeline — openlit.init() calls
# set_trace_processors([OpenLITTracingProcessor]), which both (a) emits the agent /
# generation / tool spans we want and (b) replaces the default exporter, so nothing
# is uploaded to OpenAI's backend. Disabling tracing would leave only the
# create_agent span.

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

KNOWLEDGE_BASE = {
    "kubecon": "KubeCon + CloudNativeCon India 2026 is in Mumbai. This demo shows eBPF vs SDK observability for AI agents.",
    "obi": "OpenTelemetry eBPF Instrumentation (OBI) captures GenAI HTTP traffic without code changes.",
    "openlit": "OpenLIT provides OpenTelemetry-native LLM observability with agent framework spans.",
    "accountability": "Agent accountability needs traces of tool calls, LLM requests, and decisions — not just API latency.",
}


@function_tool
def search_knowledge_base(query: str) -> str:
    """Search internal docs about observability, KubeCon, and AI agents."""
    q = query.lower()
    for key, value in KNOWLEDGE_BASE.items():
        if key in q or q in key:
            return value
    return "No exact match. Topics: " + ", ".join(KNOWLEDGE_BASE.keys())


@function_tool
def list_available_topics() -> str:
    """List topics available in the knowledge base."""
    return ", ".join(KNOWLEDGE_BASE.keys())


@function_tool
def summarize_action_plan(goal: str, steps: list[str]) -> str:
    """Produce a short accountability checklist for an agent action."""
    numbered = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(steps))
    return f"Accountability plan for '{goal}':\n{numbered}"


_agent = Agent(
    name="Research Agent",
    instructions=(
        "You are a helpful research agent for a KubeCon talk on AI agent observability. "
        "Use tools when helpful. Keep answers concise and cite which tools you used."
    ),
    model=MODEL,
    tools=[search_knowledge_base, list_available_topics, summarize_action_plan],
)


def _raw_get(raw: Any, key: str) -> Any:
    """Agents SDK ``raw_item`` is sometimes an object, sometimes a TypedDict."""
    if isinstance(raw, dict):
        return raw.get(key)
    return getattr(raw, key, None)


def _extract_tool_events(result: Any) -> list[dict[str, str]]:
    """Pull tool calls + their outputs out of the run for the UI panel."""
    events: list[dict[str, str]] = []
    pending: dict[str, dict[str, str]] = {}

    for item in getattr(result, "new_items", []) or []:
        item_type = getattr(item, "type", "")
        raw = getattr(item, "raw_item", None)

        if item_type == "tool_call_item":
            name = _raw_get(raw, "name") or ""
            arguments = _raw_get(raw, "arguments") or ""
            call_id = _raw_get(raw, "call_id") or _raw_get(raw, "id") or name
            event = {"tool": name, "arguments": arguments, "result": ""}
            pending[call_id] = event
            events.append(event)

        elif item_type == "tool_call_output_item":
            output = getattr(item, "output", None)
            if output is None:
                output = _raw_get(raw, "output")
            call_id = _raw_get(raw, "call_id")
            if call_id and call_id in pending:
                pending[call_id]["result"] = str(output)
            elif events:
                events[-1]["result"] = str(output)

    return events


async def run_agent(user_message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    input_items: list[dict[str, str]] = []
    if history:
        for item in history[-6:]:
            input_items.append({"role": item["role"], "content": item["content"]})
    input_items.append({"role": "user", "content": user_message})

    result = await Runner.run(_agent, input_items)

    return {
        "answer": result.final_output or "",
        "tool_events": _extract_tool_events(result),
        "model": MODEL,
    }

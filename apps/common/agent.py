"""Shared research agent with tool calls — demo for 'what did the agent do?'"""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

KNOWLEDGE_BASE = {
    "kubecon": "KubeCon + CloudNativeCon India 2026 is in Mumbai. This demo shows eBPF vs SDK observability for AI agents.",
    "obi": "OpenTelemetry eBPF Instrumentation (OBI) captures GenAI HTTP traffic without code changes.",
    "openlit": "OpenLIT provides OpenTelemetry-native LLM observability with agent framework spans.",
    "accountability": "Agent accountability needs traces of tool calls, LLM requests, and decisions — not just API latency.",
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search internal docs about observability, KubeCon, and AI agents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Topic to look up",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_available_topics",
            "description": "List topics available in the knowledge base.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_action_plan",
            "description": "Produce a short accountability checklist for an agent action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string"},
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["goal", "steps"],
            },
        },
    },
]


def _run_tool(name: str, arguments: str) -> str:
    args: dict[str, Any] = json.loads(arguments or "{}")

    if name == "search_knowledge_base":
        query = args.get("query", "").lower()
        for key, value in KNOWLEDGE_BASE.items():
            if key in query or query in key:
                return value
        return "No exact match. Topics: " + ", ".join(KNOWLEDGE_BASE.keys())

    if name == "list_available_topics":
        return ", ".join(KNOWLEDGE_BASE.keys())

    if name == "summarize_action_plan":
        goal = args.get("goal", "unknown goal")
        steps = args.get("steps", [])
        numbered = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(steps))
        return f"Accountability plan for '{goal}':\n{numbered}"

    return f"Unknown tool: {name}"


def run_agent(user_message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a helpful research agent for a KubeCon talk on AI agent observability. "
                "Use tools when helpful. Keep answers concise and cite which tools you used."
            ),
        },
    ]

    if history:
        for item in history[-6:]:
            messages.append({"role": item["role"], "content": item["content"]})

    messages.append({"role": "user", "content": user_message})

    tool_events: list[dict[str, str]] = []
    max_rounds = 5

    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        choice = response.choices[0]
        message = choice.message

        if not message.tool_calls:
            return {
                "answer": message.content or "",
                "tool_events": tool_events,
                "model": MODEL,
            }

        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            }
        )

        for tool_call in message.tool_calls:
            result = _run_tool(tool_call.function.name, tool_call.function.arguments)
            tool_events.append(
                {
                    "tool": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                    "result": result,
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    return {
        "answer": "Agent stopped after maximum tool rounds.",
        "tool_events": tool_events,
        "model": MODEL,
    }

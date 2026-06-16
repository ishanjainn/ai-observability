import os
import sys

sys.path.insert(0, "/app/common")

import openlit

# openlit.init() must run before the Agents SDK is used so its monkeypatch
# instrumentation is in place. It auto-instruments the OpenAI Agents SDK.
OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
openlit.init(
    otlp_endpoint=OTLP_ENDPOINT,
    service_name=os.environ.get("OTEL_SERVICE_NAME", "agent-openlit"),
    environment=os.environ.get("OTEL_DEPLOYMENT_ENVIRONMENT", "kubecon-demo"),
    # The collector pipeline only handles traces + metrics, so turn off the
    # OTLP logs/eval-logs exporters (otherwise OpenLIT logs "export logs 404").
    disable_events=True,
    evals_logs_export=False,
)

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

from agent_sdk import run_agent

app = FastAPI(title="Agent (OpenLIT + OBI)", version="1.0.0")
templates = Jinja2Templates(directory="/app/common/templates")
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    tool_events: list[dict[str, str]]
    model: str


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "mode": "openlit-sdk",
        "framework": "openai-agents",
        "otlp_endpoint": OTLP_ENDPOINT,
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "title": "Research Agent — OpenLIT + OpenAI Agents SDK",
            "subtitle": "OpenAI Agents SDK auto-instrumented by OpenLIT (agent, LLM and tool spans).",
            "mode_label": "OpenLIT SDK",
        },
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    result = await run_agent(body.message, body.history)
    return ChatResponse(**result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8081")))

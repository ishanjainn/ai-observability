import os
import sys

# Shared agent module lives alongside app packages in the image.
sys.path.insert(0, "/app/common")

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

from agent import run_agent

app = FastAPI(title="Agent (OBI only)", version="1.0.0")
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
    return {"status": "ok", "mode": "ebpf-only"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "title": "Research Agent — OBI only (zero-code)",
            "subtitle": "No OpenLIT SDK. GenAI traffic is captured by OpenTelemetry eBPF Instrumentation.",
            "mode_label": "eBPF / OBI",
        },
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    result = run_agent(body.message, body.history)
    return ChatResponse(**result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))

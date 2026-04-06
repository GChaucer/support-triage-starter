from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse

from src.agent import TriageAgent
from src.config import FRONTEND_DIR
from src.logging_config import configure_logging
from src.schemas import TriageRequest, TriageResponse


configure_logging()

app = FastAPI(title="Support Triage Starter")
agent = TriageAgent()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/triage", response_model=TriageResponse)
def triage(request: TriageRequest) -> TriageResponse:
    return agent.handle(request)

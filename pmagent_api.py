#!/usr/bin/env python3
"""
FastAPI wrapper for pmagent.py
Run:
  pip install fastapi "uvicorn[standard]" pydantic
  python -m uvicorn pmagent_api:app --reload  # http://localhost:8000
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pmagent import PMAgent

app = FastAPI(title="PM Agent API", version="0.1.0")

# Allow local dev from Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = PMAgent()


class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = ""


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/projects")
def list_projects():
    return agent.list_projects()


@app.post("/projects")
def create_project(req: CreateProjectRequest):
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    return agent.create_project(req.name, req.description or "")


@app.get("/projects/{project_id}/onboarding")
def get_onboarding(project_id: str):
    return agent.get_onboarding(project_id)


@app.patch("/projects/{project_id}/onboarding")
def save_onboarding(project_id: str, patch: Dict[str, Any] = Body(...)):
    try:
        return agent.save_onboarding_draft(project_id, patch)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/projects/{project_id}/onboarding/commit")
def commit_onboarding(project_id: str):
    try:
        return agent.commit_onboarding(project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# For direct `python pmagent_api.py` usage (optional)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("pmagent_api:app", host="0.0.0.0", port=8000, reload=True)

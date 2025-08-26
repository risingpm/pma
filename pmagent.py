#!/usr/bin/env python3
"""
PM Agent — minimal file-backed data layer with Phase‑1 Onboarding support.
Drop-in replacement for your existing pmagent.py.

Data layout (relative to CWD):
  pmagent_data/
    projects/
      <project_id>/
        project.json
        onboarding.json
"""
from __future__ import annotations

import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ----------------------------
# Utilities
# ----------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\-\s]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or f"project-{uuid.uuid4().hex[:6]}"


# shallow-safe deep merge for nested dicts

def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _compute_derived(ob: Dict[str, Any]) -> Dict[str, Any]:
    def has(path: str) -> bool:
        cur: Any = ob
        for part in path.split('.'):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return False
        if isinstance(cur, str):
            return bool(cur.strip())
        if isinstance(cur, list):
            return len(cur) > 0
        return cur is not None

    # coverage points (6): name, problem, direction (north star or primary metrics), users+usecases, milestones, artifacts
    points = [
        has('identity.name'),
        has('intent.problem_statement'),
        has('intent.north_star') or (len(ob.get('metrics', {}).get('primary_objectives', [])) > 0),
        (len(ob.get('users', {}).get('personas', [])) > 0) and (len(ob.get('intent', {}).get('top_use_cases', [])) > 0),
        len(ob.get('delivery', {}).get('milestones', [])) > 0,
        any([
            len(ob.get('artifacts', {}).get('prds', [])) > 0,
            len(ob.get('artifacts', {}).get('designs', [])) > 0,
            len(ob.get('artifacts', {}).get('tech_docs', [])) > 0,
            bool(ob.get('artifacts', {}).get('data_schema')),
        ]),
    ]
    covered = sum(1 for p in points if p)
    ci = round(covered / len(points), 2)

    nba: List[str] = []
    if not points[2]:
        nba.append("Define 1–2 primary metrics tied to the North Star")
    if not points[3]:
        nba.append("Add at least 1 persona and 1 top use case")
    if not points[4]:
        nba.append("Draft 2–3 milestones with dates and exit criteria")
    if not points[5]:
        nba.append("Link a PRD/design/tech doc or data schema")

    return {"confidence_index": ci, "next_best_actions": nba}


# ----------------------------
# PMAgent
# ----------------------------

class PMAgent:
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir: Path = Path(base_dir) if base_dir else Path(os.environ.get("PMAGENT_DATA", "./pmagent_data"))
        self.projects_dir: Path = self.base_dir / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    # ---- filesystem helpers ----
    def _project_dir(self, project_id: str) -> Path:
        p = self.projects_dir / project_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _touch_project(self, project_id: str) -> None:
        meta_path = self._project_dir(project_id) / "project.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        else:
            meta = {}
        meta.setdefault("id", project_id)
        meta["updated_at"] = now_iso()
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # ---- project CRUD ----
    def list_projects(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for p in sorted(self.projects_dir.glob("*/project.json")):
            try:
                meta = json.loads(p.read_text(encoding="utf-8"))
                meta.setdefault("id", p.parent.name)
                out.append(meta)
            except Exception:
                # skip broken files
                continue
        # sort by updated_at desc, fallback name asc
        def sort_key(m: Dict[str, Any]):
            return (
                0 - datetime.fromisoformat(m.get("updated_at", "1970-01-01T00:00:00+00:00").replace("Z", "+00:00")).timestamp(),
                m.get("name", ""),
            )
        out.sort(key=sort_key)
        return out

    def create_project(self, name: str, description: str = "") -> Dict[str, Any]:
        if not name or not name.strip():
            raise ValueError("Project name is required")
        base = slugify(name)
        # ensure uniqueness
        suffix = uuid.uuid4().hex[:6]
        project_id = f"{base}-{suffix}"
        pdir = self._project_dir(project_id)
        meta = {
            "id": project_id,
            "name": name.strip(),
            "description": description.strip() if description else "",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        (pdir / "project.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        # initialize empty onboarding draft
        if not (pdir / "onboarding.json").exists():
            (pdir / "onboarding.json").write_text(json.dumps(self._empty_onboarding(), indent=2), encoding="utf-8")
        return meta

    # ---- onboarding ----
    @staticmethod
    def _empty_onboarding() -> Dict[str, Any]:
        return {
            "identity": {"name": "", "one_line": "", "owner": {}},
            "intent": {"problem_statement": "", "north_star": "", "business_objectives": [], "out_of_scope": [], "top_use_cases": []},
            "users": {"personas": []},
            "metrics": {"primary_objectives": [], "guardrails": []},
            "delivery": {"milestones": []},
            "artifacts": {"prds": [], "designs": [], "tech_docs": [], "data_schema": None},
            "derived": {"next_best_actions": [], "confidence_index": 0.0},
        }

    def get_onboarding(self, project_id: str) -> Dict[str, Any]:
        pdir = self._project_dir(project_id)
        path = pdir / "onboarding.json"
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return self._empty_onboarding()
        return self._empty_onboarding()

    def save_onboarding_draft(self, project_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        pdir = self._project_dir(project_id)
        existing = self.get_onboarding(project_id)
        merged = _deep_merge(existing, patch)
        # update derived on every draft save
        merged["derived"] = _compute_derived(merged)
        (pdir / "onboarding.json").write_text(json.dumps(merged, indent=2), encoding="utf-8")
        self._touch_project(project_id)
        return merged

    def commit_onboarding(self, project_id: str) -> Dict[str, Any]:
        pdir = self._project_dir(project_id)
        ob = self.get_onboarding(project_id)
        # Validate required fields
        missing: List[str] = []
        if not ob.get("identity", {}).get("name", "").strip():
            missing.append("identity.name")
        if not ob.get("intent", {}).get("problem_statement", "").strip():
            missing.append("intent.problem_statement")
        if missing:
            raise ValueError("Missing required: " + ", ".join(missing))

        # Recompute derived
        ob["derived"] = _compute_derived(ob)
        (pdir / "onboarding.json").write_text(json.dumps(ob, indent=2), encoding="utf-8")

        # sync summary fields to project.json for list views
        meta_path = pdir / "project.json"
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {"id": project_id}
        meta["name"] = ob.get("identity", {}).get("name") or meta.get("name")
        # prefer one_line, then north_star, else existing description
        summary = (
            ob.get("identity", {}).get("one_line")
            or ob.get("intent", {}).get("north_star")
            or meta.get("description", "")
        )
        meta["description"] = summary
        meta["updated_at"] = now_iso()
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return ob


# ----------------------------
# Optional CLI for quick ops
# ----------------------------

def _usage() -> None:
    print(
        """
Usage:
  pmagent.py list
  pmagent.py create "Project Name" [description]
  pmagent.py onb-get <project_id>
  pmagent.py onb-save <project_id> '{"json":"patch"}'
  pmagent.py onb-commit <project_id>
        """.strip()
    )


def _main(argv: List[str]) -> int:
    ag = PMAgent()
    if len(argv) < 2:
        _usage(); return 1
    cmd = argv[1]
    try:
        if cmd == "list":
            print(json.dumps(ag.list_projects(), indent=2))
            return 0
        if cmd == "create":
            if len(argv) < 3:
                raise ValueError("Name required")
            name = argv[2]
            desc = argv[3] if len(argv) > 3 else ""
            print(json.dumps(ag.create_project(name, desc), indent=2))
            return 0
        if cmd == "onb-get":
            print(json.dumps(ag.get_onboarding(argv[2]), indent=2))
            return 0
        if cmd == "onb-save":
            project_id = argv[2]
            patch = json.loads(argv[3]) if len(argv) > 3 else {}
            print(json.dumps(ag.save_onboarding_draft(project_id, patch), indent=2))
            return 0
        if cmd == "onb-commit":
            print(json.dumps(ag.commit_onboarding(argv[2]), indent=2))
            return 0
        _usage(); return 1
    except Exception as e:
        print(f"Error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))

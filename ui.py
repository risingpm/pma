#!/usr/bin/env python3
"""Streamlit UI for PM Agent — Phase‑1 Onboarding wizard.
Copy-pasteable full app. Requires pmagent.py in the same folder.

Run:
  pip install streamlit "pydantic>=1.10,<3"
  streamlit run ui.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

# Local import
from pmagent import PMAgent

# ----------------------------
# Page setup
# ----------------------------
st.set_page_config(page_title="PM Agent", page_icon="🧭", layout="wide")

# small CSS polish
st.markdown(
    """
    <style>
      .block-container {padding-top: 1.5rem;}
      .stTabs [data-baseweb="tab-list"] button {gap: .5rem}
      .onb-card {border: 1px solid rgba(0,0,0,.08); padding: 1rem; border-radius: .75rem}
    </style>
    """,
    unsafe_allow_html=True,
)

# Ensure agent singleton
if "agent" not in st.session_state:
    st.session_state["agent"] = PMAgent()

ag: PMAgent = st.session_state["agent"]

# ----------------------------
# Sidebar — project picker / creator
# ----------------------------
with st.sidebar:
    st.header("Projects")
    projects = ag.list_projects()
    if projects:
        labels = [f"{p.get('name','<unnamed>')} — {p['id']}" for p in projects]
        ids = [p["id"] for p in projects]
        default_idx = 0
        selected_label = st.selectbox("Select a project", options=labels, index=default_idx if labels else 0)
        selected_project = ids[labels.index(selected_label)] if labels else None
    else:
        st.info("No projects yet. Create one below.")
        selected_project = None

    st.markdown("---")
    st.subheader("Create new project")
    new_name = st.text_input("Name")
    new_desc = st.text_input("One‑line (optional)")
    if st.button("Create Project", use_container_width=True, type="primary"):
        try:
            meta = ag.create_project(new_name, new_desc)
            st.success(f"Created {meta['name']}")
            selected_project = meta["id"]
            st.rerun()
        except Exception as e:
            st.error(str(e))

# carry selection in session
if selected_project:
    st.session_state["selected_project"] = selected_project
selected_project = st.session_state.get("selected_project")

# ----------------------------
# Helpers
# ----------------------------

def _lines_to_list(text: str) -> List[str]:
    return [s.strip() for s in (text or "").splitlines() if s.strip()]


def _csv_to_list(text: str) -> List[str]:
    return [s.strip() for s in (text or "").split(',') if s.strip()]


def _list_to_lines(items: List[str]) -> str:
    return "\n".join(items or [])


# ----------------------------
# Main content
# ----------------------------

st.title("PM Agent")

if not selected_project:
    st.info("Select or create a project from the sidebar to begin.")
    st.stop()

# Load metadata
proj_dir = Path("pmagent_data") / "projects" / selected_project
meta_path = proj_dir / "project.json"
if meta_path.exists():
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
else:
    meta = {"id": selected_project}

# Tabs
onb_tab, project_tab = st.tabs(["Onboarding", "Project"])  # add more later (Chat, Experiments)

# ----------------------------
# Onboarding tab
# ----------------------------
with onb_tab:
    st.subheader("Phase‑1 Onboarding")

    ob = ag.get_onboarding(selected_project)

    # per-project step state
    step_key = f"onb_step::{selected_project}"
    if step_key not in st.session_state:
        st.session_state[step_key] = 1
    step = st.session_state[step_key]

    st.progress(step / 6)
    st.caption(f"Step {step} of 6")

    def save_patch(patch: Dict[str, Any]) -> Dict[str, Any]:
        saved = ag.save_onboarding_draft(selected_project, patch)
        return saved

    # Step 1 — Basics (required)
    if step == 1:
        st.markdown("### 1) Basics")
        with st.container():
            name = st.text_input("Project Name *", value=ob.get("identity", {}).get("name") or meta.get("name", ""))
            one_line = st.text_input("One‑line (optional)", value=ob.get("identity", {}).get("one_line", meta.get("description", "")))
            problem = st.text_area(
                "Problem Statement *",
                value=ob.get("intent", {}).get("problem_statement", ""),
                height=160,
                placeholder="When [context], [user] wants to [job] so that [outcome]. Today, [pain]. We propose [approach].",
            )
        cols = st.columns(2)
        if cols[0].button("Save draft", use_container_width=True):
            save_patch({"identity": {"name": name, "one_line": one_line}, "intent": {"problem_statement": problem}})
            st.success("Draft saved.")
        if cols[1].button("Save & Continue →", use_container_width=True, type="primary"):
            if not name.strip() or not problem.strip():
                st.error("Name and Problem Statement are required.")
            else:
                save_patch({"identity": {"name": name, "one_line": one_line}, "intent": {"problem_statement": problem}})
                st.session_state[step_key] = 2
                st.rerun()

    # Step 2 — Direction
    if step == 2:
        st.markdown("### 2) Direction")
        ns = st.text_input("North Star (optional)", value=ob.get("intent", {}).get("north_star", ""))
        bos = st.text_input("Business Objectives (comma‑separated)", value=", ".join(ob.get("intent", {}).get("business_objectives", [])))
        oos = st.text_area("Out of Scope (one per line)", value=_list_to_lines(ob.get("intent", {}).get("out_of_scope", [])))
        cols = st.columns(2)
        if cols[0].button("← Back"):
            st.session_state[step_key] = 1; st.rerun()
        if cols[1].button("Save & Continue →", type="primary"):
            bo_list = _csv_to_list(bos)
            oo_list = _lines_to_list(oos)
            save_patch({"intent": {"north_star": ns, "business_objectives": bo_list, "out_of_scope": oo_list}})
            st.session_state[step_key] = 3; st.rerun()

    # Step 3 — Users & Use Cases
    if step == 3:
        st.markdown("### 3) Users & Use Cases")
        personas: List[Dict[str, Any]] = ob.get("users", {}).get("personas", [])
        st.markdown("**Personas**")
        if personas:
            for i, p in enumerate(personas):
                st.write(f"• {p.get('name','<unnamed>')}")
        new_p = st.text_input("Add persona name")
        cols = st.columns(3)
        if cols[0].button("Add Persona") and new_p.strip():
            personas.append({"name": new_p.strip()})
            save_patch({"users": {"personas": personas}})
            st.rerun()
        if cols[1].button("← Back"):
            st.session_state[step_key] = 2; st.rerun()
        if cols[2].button("Continue →", type="primary"):
            st.session_state[step_key] = 4; st.rerun()

        st.markdown("---")
        tuc: List[Dict[str, Any]] = ob.get("intent", {}).get("top_use_cases", [])
        st.markdown("**Top Use Cases**")
        if tuc:
            for uc in tuc:
                sc = uc.get("success_criteria", [])
                st.write(f"• {uc.get('title')} — success: {', '.join(sc) if sc else 'n/a'}")
        title = st.text_input("Use case title")
        sc = st.text_area("Success criteria (one per line)")
        if st.button("Add Use Case") and title.strip():
            tuc.append({"title": title.strip(), "success_criteria": _lines_to_list(sc)})
            save_patch({"intent": {"top_use_cases": tuc}})
            st.rerun()

    # Step 4 — Metrics
    if step == 4:
        st.markdown("### 4) Metrics — Primary Objectives & Guardrails")
        po: List[Dict[str, Any]] = ob.get("metrics", {}).get("primary_objectives", [])
        gr: List[Dict[str, Any]] = ob.get("metrics", {}).get("guardrails", [])

        st.markdown("**Primary Objectives**")
        if po:
            for i, m in enumerate(po):
                st.write(f"• {m.get('name')} — target: {m.get('target')} {m.get('unit','')}")
        with st.expander("Add Primary Objective"):
            mname = st.text_input("Metric name", key=f"po_name_{selected_project}")
            mdef = st.text_input("Definition", key=f"po_def_{selected_project}")
            unit = st.text_input("Unit", key=f"po_unit_{selected_project}")
            baseline = st.text_input("Baseline (number)", key=f"po_base_{selected_project}")
            target = st.text_input("Target (number)", key=f"po_target_{selected_project}")
            tdate = st.text_input("Target date (YYYY‑MM‑DD)", key=f"po_date_{selected_project}")
            if st.button("Add Metric") and mname.strip():
                def to_float(s: str):
                    try: return float(s)
                    except: return None
                po.append({
                    "name": mname.strip(),
                    "definition": mdef.strip() or None,
                    "unit": unit.strip() or None,
                    "baseline": to_float(baseline),
                    "target": to_float(target),
                    "target_date": tdate.strip() or None,
                })
                save_patch({"metrics": {"primary_objectives": po}})
                st.rerun()

        st.markdown("**Guardrails**")
        if gr:
            for g in gr:
                st.write(f"• {g.get('name')} — threshold: {g.get('threshold')} {g.get('unit','')} ({g.get('direction')})")
        with st.expander("Add Guardrail"):
            gname = st.text_input("Guardrail name", key=f"gr_name_{selected_project}")
            gdef = st.text_input("Definition", key=f"gr_def_{selected_project}")
            gunit = st.text_input("Unit", key=f"gr_unit_{selected_project}")
            gthr = st.text_input("Threshold (number)", key=f"gr_thr_{selected_project}")
            gdir = st.selectbox("Direction", ["min", "max"], index=0, key=f"gr_dir_{selected_project}")
            if st.button("Add Guardrail") and gname.strip():
                def to_float(s: str):
                    try: return float(s)
                    except: return None
                gr.append({
                    "name": gname.strip(),
                    "definition": gdef.strip() or None,
                    "unit": gunit.strip() or None,
                    "threshold": to_float(gthr),
                    "direction": gdir,
                })
                save_patch({"metrics": {"guardrails": gr}})
                st.rerun()

        cols = st.columns(2)
        if cols[0].button("← Back"):
            st.session_state[step_key] = 3; st.rerun()
        if cols[1].button("Continue →", type="primary"):
            st.session_state[step_key] = 5; st.rerun()

    # Step 5 — Milestones
    if step == 5:
        st.markdown("### 5) Milestones")
        ms: List[Dict[str, Any]] = ob.get("delivery", {}).get("milestones", [])
        if ms:
            for m in ms:
                st.write(f"• {m.get('name')} — {m.get('date') or 'no date'}")
        name = st.text_input("Milestone name")
        date = st.text_input("Date (YYYY‑MM‑DD)")
        ec = st.text_area("Exit criteria (one per line)")
        cols = st.columns(3)
        if cols[0].button("Add Milestone") and name.strip():
            ms.append({"name": name.strip(), "date": date.strip() or None, "exit_criteria": _lines_to_list(ec)})
            save_patch({"delivery": {"milestones": ms}})
            st.rerun()
        if cols[1].button("← Back"):
            st.session_state[step_key] = 4; st.rerun()
        if cols[2].button("Continue →", type="primary"):
            st.session_state[step_key] = 6; st.rerun()

    # Step 6 — Artifacts + Review
    if step == 6:
        st.markdown("### 6) Artifacts & Review")
        ar = ob.get("artifacts", {})
        prds = st.text_area("PRD links (one per line)", value=_list_to_lines(ar.get("prds", [])))
        designs = st.text_area("Design links (one per line)", value=_list_to_lines(ar.get("designs", [])))
        tech = st.text_area("Tech doc links (one per line)", value=_list_to_lines(ar.get("tech_docs", [])))
        ds_type = st.selectbox("Data schema type", ["none", "link", "inline"], index=0)
        ds_val = st.text_area("Data schema value (URL or inline DDL)", value=(ar.get("data_schema", {}) or {}).get("value", ""))

        if st.button("Save Artifacts"):
            payload = {
                "artifacts": {
                    "prds": _lines_to_list(prds),
                    "designs": _lines_to_list(designs),
                    "tech_docs": _lines_to_list(tech),
                    "data_schema": None if ds_type == "none" else {"type": ds_type, "value": ds_val.strip()},
                }
            }
            ob = save_patch(payload)
            st.success("Artifacts saved.")

        st.markdown("---")
        cov = ob.get("derived", {}).get("confidence_index", 0)
        st.metric("Confidence Index", f"{int((cov or 0)*100)}%")
        nba = ob.get("derived", {}).get("next_best_actions", [])
        if nba:
            st.markdown("**Next best actions**")
            for i, item in enumerate(nba, 1):
                st.write(f"{i}. {item}")

        cols = st.columns(3)
        if cols[0].button("← Back"):
            st.session_state[step_key] = 5; st.rerun()
        if cols[2].button("✅ Commit Onboarding", type="primary"):
            try:
                final = ag.commit_onboarding(selected_project)
                st.success("Onboarding committed! You can navigate away or continue editing.")
            except Exception as e:
                st.error(str(e))

# ----------------------------
# Project tab — read-only views
# ----------------------------
with project_tab:
    st.subheader("Project Files")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**project.json**")
        try:
            st.json(json.loads((proj_dir / "project.json").read_text(encoding="utf-8")))
        except Exception:
            st.write("(missing)")
    with col2:
        st.markdown("**onboarding.json**")
        try:
            st.json(json.loads((proj_dir / "onboarding.json").read_text(encoding="utf-8")))
        except Exception:
            st.write("(missing)")

    st.caption("Files are stored under ./pmagent_data/projects/<project_id>/ …")

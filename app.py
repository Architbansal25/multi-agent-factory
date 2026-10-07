"""Streamlit front end for the human-gated engineering factory.

    streamlit run app.py

Submit a brief, watch the agents work, and answer both human gates from the
browser instead of the terminal. Runs happen in a background worker process
(services/ui_worker.py) and every bit of progress shown here is read from the
project's disk memory, so closing the tab never loses a run.
"""
from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
import yaml

from crew import BUILD_NOW, PLAN_GATES
from services.orchestration import State
from services.ui_runner import ProjectRun, compose_brief, list_projects, pending_gate, pipeline, slugify
from tasks.speckit_tasks import ARCHITECTURE_PLAN, PACKAGING

BASE_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = BASE_DIR / "projects"
NEW_PROJECT = "+ New project"
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"}

AGENT_NAMES = {"manager": "Manager", "architect": "Architect", "senior_developer": "Senior Developer"}
STATE_TEXT = {
    State.DRAFTING_PROPOSAL.value: "is drafting a plan for your review",
    State.PROPOSAL_REVISION.value: "is revising the plan with your feedback",
    State.AWAITING_PROPOSAL_APPROVAL.value: "is waiting for your decision",
    State.EXECUTING.value: "is writing the deliverable",
    State.OUTPUT_REVISION.value: "is fixing output the guardrails rejected",
    State.AWAITING_OUTPUT_APPROVAL.value: "is waiting for your decision on the output",
    State.STAGE_COMPLETE.value: "is publishing the approved output",
}
LANGUAGES = {".py": "python", ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
             ".ts": "typescript", ".tsx": "tsx", ".jsx": "jsx", ".json": "json", ".html": "html",
             ".css": "css", ".scss": "scss", ".md": "markdown", ".yaml": "yaml", ".yml": "yaml",
             ".sh": "bash", ".sql": "sql", ".toml": "toml", ".java": "java", ".go": "go",
             ".rs": "rust", ".rb": "ruby", ".php": "php", ".cs": "csharp", ".xml": "xml"}

st.set_page_config(page_title="Engineering Factory", page_icon="🏭", layout="wide")
st.markdown("""
<style>
.flow { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 4px 0 12px; }
.chip { padding: 4px 10px; border-radius: 999px; font-size: 0.82rem; white-space: nowrap;
        border: 1px solid rgba(128,128,128,0.35); }
.chip.done { background: rgba(33,150,83,0.16); border-color: rgba(33,150,83,0.55); }
.chip.active { background: rgba(30,120,230,0.18); border-color: rgba(30,120,230,0.7); font-weight: 600; }
.chip.waiting { background: rgba(240,160,20,0.22); border-color: rgba(240,160,20,0.8); font-weight: 600; }
.chip.skipped { opacity: 0.45; text-decoration: line-through; }
.chip.pending { opacity: 0.7; }
.arrow { opacity: 0.45; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- helpers
def api_key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY") or st.session_state.get("api_key", "")


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def ago(stamp: str | None) -> str:
    if not stamp:
        return ""
    try:
        seconds = int((datetime.now(timezone.utc) - datetime.fromisoformat(stamp)).total_seconds())
    except ValueError:
        return ""
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60:02d}s"


def clock(stamp: str | None) -> str:
    try:
        return datetime.fromisoformat(stamp).astimezone().strftime("%H:%M:%S")
    except (TypeError, ValueError):
        return ""


def launch(run: ProjectRun, **kwargs) -> None:
    if not api_key():
        st.error("Enter your Anthropic API key in the sidebar first.")
        return
    try:
        run.launch(BASE_DIR, api_key(), **kwargs)
    except RuntimeError as exc:
        st.error(str(exc))
        return
    st.rerun()


def project_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not SKIP_DIRS.intersection(path.relative_to(root).parts):
            files.append(path)
    return files


def zip_folder(root: Path, folders: tuple[str, ...]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder in folders:
            for path in project_files(root / folder):
                archive.write(path, path.relative_to(root).as_posix())
    return buffer.getvalue()


# ---------------------------------------------------------------- sidebar
def sidebar() -> ProjectRun | None:
    with st.sidebar:
        st.title("🏭 Engineering Factory")
        st.caption("Three agents, two human gates. You approve every plan before code is written.")

        if os.environ.get("ANTHROPIC_API_KEY"):
            st.success("API key loaded from ANTHROPIC_API_KEY", icon="🔑")
        else:
            st.text_input("Anthropic API key", type="password", key="api_key",
                          help="Kept in this browser session only and passed to the worker process. "
                               "Never written to disk.")

        projects = list_projects(BASE_DIR, PROJECTS_DIR)
        labels = [NEW_PROJECT] + [path.relative_to(BASE_DIR).as_posix() for path in projects]
        opened = st.session_state.pop("open_project", None)
        if opened:
            st.session_state.project_choice = opened
        current = st.session_state.get("project_choice")
        if current and current not in labels:
            # Just created: listed once the worker has written memory/context.json.
            labels.insert(1, current)
        choice = st.selectbox("Project", labels, key="project_choice")
        st.session_state.project = None if choice == NEW_PROJECT else choice

        config_path = BASE_DIR / "agents.config.yaml"
        if st.session_state.project:
            override = BASE_DIR / st.session_state.project / "agents.config.yaml"
            config_path = override if override.exists() else config_path
        try:
            agents = yaml.safe_load(read(config_path)).get("agents", {})
            with st.expander("Agent models"):
                for name, entry in agents.items():
                    st.markdown(f"**{AGENT_NAMES.get(name, name)}**  \n`{entry.get('model', '?')}`")
        except (AttributeError, yaml.YAMLError):
            st.warning("Could not read agents.config.yaml")

    return ProjectRun(BASE_DIR / st.session_state.project) if st.session_state.project else None


# ---------------------------------------------------------------- new project
def new_project() -> None:
    st.header("Start a new build")
    st.write("Describe what you want built. The Architect will come back with a plan for your "
             "approval before anything is generated.")

    mode = st.radio("Write the brief with", ["Guided form", "Markdown"], horizontal=True)
    with st.form("brief"):
        name = st.text_input("Project name", placeholder="book-library",
                             help="Output goes to projects/<name>/. Use a new name for every new brief.")
        if mode == "Guided form":
            problem = st.text_area("Problem statement", height=140,
                                   placeholder="WHAT you want built and WHY. Avoid tech-stack details here.")
            constraints = st.text_area("System constraints (one per line)", height=110,
                                       placeholder="A Node.js + Express backend exposing a REST API.\n"
                                                   "A JSON file acting as the data store (no database).")
            st.markdown("**Mandatory tech stack** - the exact choices the agents must use")
            stack = st.data_editor(
                [{"Constraint": "Runtime", "Rule": ""}, {"Constraint": "Web framework", "Rule": ""},
                 {"Constraint": "Data store", "Rule": ""}, {"Constraint": "Frontend", "Rule": ""}],
                num_rows="dynamic", use_container_width=True, key="stack_rows")
            criteria = st.text_area("Acceptance criteria (one per line)", height=110,
                                    placeholder="Launching the app serves a page in the browser.")
            upload = None
        else:
            upload = st.file_uploader("Upload a brief (.md)", type=["md", "markdown", "txt"])
            markdown = st.text_area("...or write it here", value=read(BASE_DIR / "INSTRUCTIONS.md"),
                                    height=420)
        submitted = st.form_submit_button("Submit brief and start the agents", type="primary")

    if not submitted:
        return
    if mode == "Guided form":
        if not problem.strip():
            st.error("Describe the problem to solve.")
            return
        brief = compose_brief(problem, constraints, stack, criteria)
    else:
        brief = upload.getvalue().decode("utf-8") if upload else markdown
    slug = slugify(name)
    if not slug:
        st.error("Give the project a name.")
        return
    if not brief.strip():
        st.error("The brief is empty.")
        return
    run = ProjectRun(PROJECTS_DIR / slug)
    if run.exists:
        st.error(f"projects/{slug} already exists. Open it from the sidebar or pick another name.")
        return
    if not api_key():
        st.error("Enter your Anthropic API key in the sidebar first.")
        return
    run.ui.mkdir(parents=True, exist_ok=True)
    run.brief_path.write_text(brief, encoding="utf-8")
    st.session_state.open_project = run.root.relative_to(BASE_DIR).as_posix()
    launch(run)


# ---------------------------------------------------------------- live progress
def render_flow(context: dict) -> None:
    icons = {"done": "✅", "active": "⏳", "waiting": "✋", "skipped": "", "pending": "○"}
    steps = pipeline(context)
    chips = []
    for index, step in enumerate(steps):
        label = ("🚦 " if step["gate"] else "") + step["label"]
        chips.append(f'<span class="chip {step["status"]}">{icons[step["status"]]} {label}</span>')
        if index < len(steps) - 1:
            chips.append('<span class="arrow">→</span>')
    st.markdown(f'<div class="flow">{"".join(chips)}</div>', unsafe_allow_html=True)
    counted = [step for step in steps if step["status"] != "skipped"]
    done = sum(step["status"] == "done" for step in counted)
    st.progress(done / max(len(counted), 1), text=f"{done} of {len(counted)} steps complete")


def describe(event: dict) -> str:
    item = event.get("item", "")
    kind = event.get("event")
    if kind == "initialized":
        return "🆕 Project created from your brief"
    if kind == "proposal":
        return f"📝 **{item}** - plan drafted, ready for review"
    if kind == "output":
        return f"📦 **{item}** - deliverable produced, checking guardrails"
    if kind == "validation_rejected":
        return f"⚠️ **{item}** - rejected by guardrails, retrying: _{str(event.get('feedback', ''))[:300]}_"
    if kind == "approved":
        mode = f" ({event['mode']})" if event.get("mode") else ""
        return f"✅ **{item}** - you approved{mode}"
    if kind == "revision":
        return f"✏️ **{item}** - you asked for changes: _{str(event.get('feedback', ''))[:300]}_"
    if kind == "stage_complete":
        return f"🏁 **{item}** - published"
    if kind == "paused":
        return f"⏸ Paused at **{item}**"
    if kind == "tests_skipped":
        return f"⏭ Tests skipped (build-now): {len(event.get('paths', []))} paths dropped"
    if kind == "blocked":
        return f"🛑 {AGENT_NAMES.get(event.get('agent'), event.get('agent'))} escalated: {event.get('reason')}"
    if kind == "invalid_approval":
        return f"❓ **{item}** - answer not recognised, asked again"
    if kind == "reopen_requested":
        return f"↩️ Reopen requested for **{event.get('target')}**"
    if kind == "decisions_reopened":
        return f"↩️ Reopened **{event.get('target')}**; invalidated {', '.join(event.get('affected', []))}"
    return f"• {kind} {item}"


def render_live(root: str, was_running: bool) -> None:
    run = ProjectRun(Path(root))
    status = run.status()
    running = status.get("state") == "running"
    if was_running and not running:
        st.rerun(scope="app")
    context = run.context()
    active = context.get("active_item") or {}

    if running:
        agent = AGENT_NAMES.get(context.get("current_agent"), "The team")
        doing = STATE_TEXT.get(active.get("state"), "is starting up")
        item = f" on **{active['id']}**" if active.get("id") else ""
        left, right = st.columns([5, 1])
        left.info(f"⏳ **{agent}** {doing}{item} · running for {ago(status.get('started_at'))}")
        if right.button("Stop", use_container_width=True, help="Stops after the current check; "
                        "everything approved so far is kept and you can resume later."):
            run.request_stop()
            st.toast("Stop requested")
        if active.get("last_rejection"):
            st.warning(f"Attempt {active.get('validation_failures', 0) + 1} of 3 - the guardrails rejected "
                       f"the previous output: {active['last_rejection']}")

    if context:
        render_flow(context)

    activity, log = st.columns([1, 1])
    with activity:
        st.markdown("**Activity**")
        with st.container(height=360, border=True):
            events = run.events()
            if not events:
                st.caption("Nothing yet.")
            for event in reversed(events[-60:]):
                st.markdown(f"<small>{clock(event.get('timestamp'))}</small> {describe(event)}",
                            unsafe_allow_html=True)
    with log:
        st.markdown("**Agent log** <small>(latest output)</small>", unsafe_allow_html=True)
        text = run.log_tail().rstrip()
        with st.container(height=360, border=True):
            # Newest lines only, so the current step is visible without scrolling.
            st.code("\n".join(text.splitlines()[-40:]) or "No output yet.", language="text",
                    wrap_lines=True)
        if text:
            with st.expander("Full agent log"):
                st.code(text, language="text", wrap_lines=True)


# ---------------------------------------------------------------- human gate
def render_gate(run: ProjectRun, item: str, gate: str) -> None:
    heading, commitment, _ = PLAN_GATES.get(item, (f"{item}: {gate.upper()} APPROVAL", "", None))
    review = run.memory / "reviews" / item
    content = read(review / ("proposal.md" if gate == "proposal" else "output.json"))

    with st.container(border=True):
        st.subheader(f"✋ {heading}")
        st.write("The agents have stopped and are waiting for you. Nothing after this point runs "
                 "until you approve.")
        if commitment:
            st.caption(commitment)

        raw = st.toggle("Show raw text", key=f"raw-{item}-{gate}")
        with st.container(height=520, border=True):
            document = None
            try:
                document = json.loads(content)
            except json.JSONDecodeError:
                pass
            if isinstance(document, dict) and isinstance(document.get("files"), dict):
                for path, text in document["files"].items():
                    st.markdown(f"##### `{path}`")
                    if raw:
                        st.code(text)
                    else:
                        st.markdown(text)
                st.json({key: value for key, value in document.items() if key != "files"})
            elif raw:
                st.code(content, language="markdown")
            else:
                st.markdown(content or "_The plan file is missing._")

        history = [json.loads(line) for line in read(review / f"{gate}_revisions.jsonl").splitlines() if line]
        if history:
            with st.expander(f"Your earlier feedback on this plan ({len(history)})"):
                for number, revision in enumerate(history, 1):
                    st.markdown(f"{number}. {revision['feedback']}")

        is_gate_one = item == ARCHITECTURE_PLAN.name
        approve, build_now = st.columns(2)
        if approve.button("✅ Approve", type="primary", use_container_width=True,
                          help="Lock this plan and build everything it describes."):
            run.queue_answer(item, gate, "approve")
            launch(run)
        if is_gate_one and build_now.button(
                "⚡ Approve build-now", use_container_width=True,
                help="Skip the PRD, FR, NFR, HLD, ADRs and tests and build straight from this plan. "
                     "Roughly a fifth of the cost; for prototypes, not upkeep."):
            run.queue_answer(item, gate, f"approve {BUILD_NOW}")
            launch(run)
        if is_gate_one:
            st.caption("**Build-now** skips the specification documents and generates **no tests**.")

        with st.form(f"revise-{item}-{gate}", clear_on_submit=True):
            feedback = st.text_area("Request changes", placeholder="Answer the open decisions or say what "
                                    "to change. The same agent re-plans with your exact words.")
            if st.form_submit_button("✏️ Send back with changes"):
                if feedback.strip():
                    run.queue_answer(item, gate, "revise " + feedback.strip())
                    launch(run)
                else:
                    st.error("Write the changes you want first.")


def render_controls(run: ProjectRun, status: dict, context: dict) -> None:
    state = status.get("state")
    completed = context.get("completed_items", {})
    gate = pending_gate(context)
    finished = PACKAGING.name in completed and not context.get("active_item")

    if state == "failed" or state == "crashed":
        st.error(status.get("message", "The run failed."))
    elif state in {"paused", "stopped"}:
        st.warning(status.get("message", "Paused."))

    if gate:
        render_gate(run, *gate)
    elif finished:
        st.success("🎉 Delivery complete. Generated tests have **not** been executed - review the "
                   "commands in the Delivery tab before running them.")
    elif context or run.brief_path.exists():
        label = "🔁 Retry from the last saved step" if state in {"failed", "crashed"} else "▶️ Resume"
        if st.button(label, type="primary"):
            launch(run)

    if completed and not gate:
        with st.expander("↩️ Reopen an approved decision"):
            st.caption("The Manager proposes the reroute for your approval; downstream artifacts are "
                       "archived under memory/superseded/ and rebuilt.")
            with st.form("reopen"):
                target = st.selectbox("Decision to reopen", list(completed))
                feedback = st.text_area("Why / what should change")
                if st.form_submit_button("Reopen"):
                    if feedback.strip():
                        launch(run, reopen=target, feedback=feedback.strip())
                    else:
                        st.error("Feedback is required to reopen a decision.")


# ---------------------------------------------------------------- outputs
def render_outputs(run: ProjectRun) -> None:
    documents, source, delivery, brief = st.tabs(["📄 Plans & documents", "💻 Source code",
                                                  "📦 Delivery", "🧾 Brief"])
    memory = run.memory
    with documents:
        candidates = [memory / "02_architecture_plan.md", memory / "01_prd.md",
                      memory / "03_architecture" / "fr.md", memory / "03_architecture" / "nfr.md",
                      memory / "03_architecture" / "hld.md",
                      *sorted((memory / "03_architecture" / "tradeoffs").glob("*.md")),
                      memory / "04_implementation_plan.md"]
        available = [path for path in candidates if path.exists()]
        drafts = sorted(path for path in (memory / "reviews").glob("*/proposal.md")
                        if not (memory / "reviews" / path.parent.name / "approved_plan.md").exists())
        available += drafts
        if not available:
            st.caption("Documents appear here as the agents write them.")
        else:
            labels = [path.relative_to(run.root).as_posix() + ("  (draft)" if path in drafts else "")
                      for path in available]
            chosen = st.selectbox("Document", labels, key="doc")
            text = read(available[labels.index(chosen)])
            if st.toggle("Raw markdown", key="doc-raw"):
                st.code(text, language="markdown")
            else:
                st.markdown(text)

    with source:
        files = project_files(run.root / "src")
        if not files:
            st.caption("Source code is written after you approve the implementation plan (gate 2).")
        else:
            st.download_button("⬇️ Download src/ as zip", zip_folder(run.root, ("src",)),
                               file_name=f"{run.root.name}-src.zip", mime="application/zip")
            labels = [path.relative_to(run.root).as_posix() for path in files]
            left, right = st.columns([1, 3])
            with left:
                chosen = st.radio(f"{len(files)} files", labels, key="src-file",
                                  label_visibility="visible")
            with right:
                path = files[labels.index(chosen)]
                st.markdown(f"**`{chosen}`**")
                st.code(read(path) or "(binary or empty file)", language=LANGUAGES.get(path.suffix.lower()),
                        line_numbers=True)

    with delivery:
        notes = read(memory / "06_delivery.md")
        if notes:
            st.download_button("⬇️ Download the whole project (src + memory)",
                               zip_folder(run.root, ("src", "memory")),
                               file_name=f"{run.root.name}.zip", mime="application/zip")
            st.markdown(notes)
        else:
            st.caption("The Manager writes the delivery notes as the last step.")

    with brief:
        st.markdown(run.brief() or "_No brief._")


# ---------------------------------------------------------------- page
def project_view(run: ProjectRun) -> None:
    status = run.status()
    running = status.get("state") == "running"
    st.header(run.root.name)
    st.caption(f"`{run.root.relative_to(BASE_DIR).as_posix()}`")
    st.fragment(render_live, run_every=2.0 if running else None)(str(run.root), running)
    if not running:
        render_controls(run, status, run.context())
    render_outputs(run)


def main() -> None:
    run = sidebar()
    if run is None:
        new_project()
    else:
        project_view(run)


main()

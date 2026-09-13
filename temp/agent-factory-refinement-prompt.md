# Prompt for Copilot: Refactor the Multi-Agent App Factory into an Industry-Grade, Human-Gated Orchestration System

> **How to use this file:** Paste everything below the line `=== PROMPT START ===` into Copilot Chat (or save it as `.github/copilot-instructions.md` / feed it as the system prompt for your orchestrator's own dev task). It is written as a direct engineering brief so Copilot can act on it without further translation from you. Sections marked `[TEMPLATE]` are reference artifacts Copilot should copy into the repo as-is (agent prompts, doc templates, config), not paraphrase.

=== PROMPT START ===

## 0. Context

You are refactoring an existing repository that implements a **multi-agent AI app factory**: a pipeline of LLM-backed agents (currently: Manager/Orchestrator, Architect, Senior Developer) that take a natural-language brief plus an `instructions.md` (stack, constraints) and produce a working application.

Current state: the factory works end-to-end but produces prototype-quality output — single-file code, stack ignored (always defaults to Python regardless of `instructions.md`), no human checkpoint between agent stages, all agents share one hardcoded LLM, and there's no formal architecture documentation stage.

Your job is a **targeted refactor**, not a rewrite. Preserve existing agent logic where it isn't broken; change the orchestration state machine, the shared memory contract, the config schema, the folder output structure, and the agent system prompts, per the spec below.

Do all of the following in order. Do not skip the stack-lock or approval-gate sections — those are the two root causes of the quality problems described.

---

## 1. Orchestrator (Manager) Agent — state machine

Replace whatever hands off agents today with an explicit state machine the Manager drives. Each **stage** (Requirements → Architecture → Development → [optional QA] → Packaging) goes through the same two-gate cycle, never skipping either gate:

```
DRAFTING_PROPOSAL
   → agent writes a short, scoped "Task Proposal": what it's about to do, which
     inputs/decisions it's relying on from shared memory, and what deliverable
     it will produce.
AWAITING_PROPOSAL_APPROVAL
   → Manager shows the proposal to the human. Human either approves, or gives
     a hint/change request.
   → if changes requested: append the feedback (with timestamp) to the
     proposal's revision log, send back to the same agent → PROPOSAL_REVISION
   → PROPOSAL_REVISION loops back to AWAITING_PROPOSAL_APPROVAL until approved
EXECUTING
   → only after proposal approval, agent produces the actual deliverable
     (code / doc / diagram)
AWAITING_OUTPUT_APPROVAL
   → Manager shows the deliverable to the human. Same accept/revise loop as
     above, appended to the deliverable's own revision log.
STAGE_COMPLETE
   → Manager writes final artifact + full revision history into shared memory,
     marks the stage closed, and hands off to the next agent with the updated
     shared memory attached.
```

Key rule: **an agent never touches "execution" until its proposal is explicitly approved**, and a stage is never marked complete until its deliverable is explicitly approved. Both gates are mandatory, not just the final one — this is what's currently missing and why bad direction only gets caught after the fact (or not at all).

The Manager owns this loop for every agent, including itself when it's making orchestration-level decisions (e.g. deciding stage order or re-routing after a revision).

---

## 2. Shared memory contract

All agents read from and write to a single memory folder — this **is** the shared context window; don't reinvent a separate in-memory context object that can drift from what's on disk.

```
memory/
  00_brief.md               # original user request, verbatim
  01_prd.md                 # product requirements doc
  02_kickoff_plan.md
  03_architecture/
      fr.md                 # functional requirements
      nfr.md                # non-functional requirements
      hld.md                # high-level design (incl. Mermaid diagram)
      tradeoffs/             # one ADR file per significant decision
          0001-<slug>.md
  04_task_log.jsonl         # append-only: every proposal, approval, revision
  05_handoff_log.md         # human-readable summary per stage handoff
  context.json              # machine-readable current state (see schema below)
src/
  ...                       # actual generated application, modular (see §5)
```

`context.json` schema — every agent's prompt must instruct it to read this before doing anything:

```json
{
  "project_name": "string",
  "stage": "requirements | architecture | development | qa | packaging",
  "current_agent": "manager | architect | senior_developer | qa_reviewer",
  "locked_stack": {
    "language": "string",
    "framework": "string",
    "database": "string",
    "infra": "string",
    "locked_at_stage": "string",
    "locked_by": "human_approved"
  },
  "global_constraints": ["from instructions.md, verbatim list"],
  "approved_decisions": [
    {"stage": "architecture", "decision": "string", "approved_at": "iso8601"}
  ],
  "open_revisions": [
    {"stage": "string", "feedback": "string", "raised_at": "iso8601", "resolved": false}
  ]
}
```

Rule for every agent prompt: *"Before producing anything, read `memory/context.json` and every file under `memory/` relevant to prior stages. Never contradict a decision already marked `approved_decisions` unless the human has explicitly reopened it."*

---

## 3. Fixing the stack problem (Python-default bug)

Root cause: the stack named in `instructions.md` is read once, loosely, and never re-asserted downstream, so each agent falls back to what it defaults to.

Fix — add a **stack-lock step** at kickoff, before the Manager even starts the Requirements stage:

1. Manager parses `instructions.md` and extracts language/framework/db/infra explicitly.
2. Manager writes this into `context.json.locked_stack` and surfaces it to the human as its own tiny proposal ("I've read the stack as: X/Y/Z — confirm?") before continuing. This is a one-time extra gate but it's cheap and prevents the whole pipeline drifting.
3. Every downstream agent's system prompt includes, verbatim, a hard constraint block:

```
HARD CONSTRAINT — TECH STACK:
You MUST build using exactly this stack: {locked_stack}.
Do not substitute, "simplify to", or default to any other language or
framework under any circumstance, including for prototypes or examples.
If the task as given seems to conflict with this stack, stop and ask the
Manager to raise it with the human instead of silently choosing your own.
```

4. The Architect's Task Proposal (see §1) must restate the locked stack explicitly, so it gets reconfirmed as part of proposal approval — a second checkpoint before any code exists.

---

## 4. Per-agent model configuration

Replace the single shared model setting with a per-agent config. Example:

```yaml
# agents.config.yaml
agents:
  manager:
    role: Orchestrator
    model_tier: mid
    model: <mid-tier model id available in your setup>
  architect:
    role: Solutions Architect
    model_tier: high
    model: <high-tier model id, e.g. Sonnet-class>
  senior_developer:
    role: Senior Software Engineer
    model_tier: high
    model: <high-tier model id, e.g. Sonnet-class>
  qa_reviewer:            # optional stage, see §8
    role: QA / Code Reviewer
    model_tier: high
    model: <high-tier model id>
```

Load this at startup; every agent invocation must resolve its model from this file rather than a global default. Keep it overridable per-project (a project can pin a different model without touching agent logic).

---

## 5. Modular code output (`src/`)

No more single-file output. The Architect's HLD (§7) must include a proposed module/file tree appropriate to the locked stack, e.g. for a typical web app:

```
src/
  backend/
    app/
      api/            # routes/controllers
      services/       # business logic
      models/         # data models / ORM
      config/
    tests/
  frontend/
    src/
      components/
      pages/
      services/       # API clients
      state/
    tests/
```

Rule: the Senior Developer agent must follow the exact tree the Architect proposed and the human approved — it may not restructure it without a new proposal+approval cycle. This ties code generation to something the human already signed off on, instead of the model inventing structure ad hoc per file.

---

## 6. Architect artifacts (required deliverables for the Architecture stage)

The Architect's stage is not complete until all four of these exist under `memory/03_architecture/` and are approved:

### 6.1 `fr.md` [TEMPLATE]
```markdown
# Functional Requirements

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-01 | ... | Must | ... |
```

### 6.2 `nfr.md` [TEMPLATE]
```markdown
# Non-Functional Requirements

| Category | Target | Rationale |
|----------|--------|-----------|
| Performance | e.g. p95 API latency < 200ms | ... |
| Scalability | e.g. handle N concurrent users | ... |
| Security | e.g. auth model, data protection | ... |
| Availability | e.g. uptime target | ... |
| Maintainability | e.g. test coverage floor | ... |
```

### 6.3 `hld.md` [TEMPLATE]
```markdown
# High-Level Design

## Component Diagram
​```mermaid
graph TD
  Client --> API
  API --> Service
  Service --> DB[(Database)]
​```

## Module / File Tree
(proposed src/ layout — see §5)

## Key Flows
(sequence diagrams for the 2-3 most important flows)
```

### 6.4 `tradeoffs/000N-<slug>.md` — one ADR per significant decision [TEMPLATE]
```markdown
# ADR-000N: <Decision Title>

## Context
What forced this decision.

## Decision
What was chosen.

## Alternatives Considered
- Option A — pros/cons
- Option B — pros/cons

## Consequences
What this makes easier/harder going forward.
```

All four go through the same proposal→execute→approve cycle as any other deliverable, not a single combined approval.

---

## 7. Refined agent system prompts

Replace the current agent prompts with the following as a base (adapt names/tools to your actual implementation, but keep the role, constraints, and interaction protocol intact):

### 7.1 Manager / Orchestrator [TEMPLATE]
```
You are the Orchestrator of a multi-agent software factory. You do not write
requirements, architecture, or code yourself — you sequence the agents who do,
enforce the shared-memory contract, and run the two-gate human approval loop
(proposal approval, then deliverable approval) for every stage without
exception.

Responsibilities:
- Read memory/context.json at the start of every action.
- Never let an agent execute a task before its proposal is approved.
- Append all human feedback to the relevant revision log before re-invoking
  an agent; never silently drop or summarize away a feedback item.
- Enforce the locked tech stack on every downstream agent invocation.
- On stage completion, write final state to memory/ and hand off with full
  context, not just the latest artifact.
- Keep the human informed at every gate with a short, specific summary —
  never batch multiple stages' approvals into one prompt.
```

### 7.2 Architect [TEMPLATE]
```
You are a Solutions Architect. Given the approved PRD and the locked tech
stack, you produce: functional requirements (fr.md), non-functional
requirements (nfr.md), a high-level design with diagrams and a proposed
module/file tree (hld.md), and architecture decision records for every
non-trivial choice (tradeoffs/*.md).

Constraints:
- You MUST use the locked stack exactly as given in memory/context.json.
- Before producing any artifact, submit a Task Proposal describing what
  you're about to design and why, and wait for approval.
- Design for production use, not a demo: consider failure modes, data
  consistency, security boundaries, and how the system will be tested and
  deployed, not just the happy path.
- Your proposed file tree becomes binding for the Senior Developer agent;
  do not leave it vague.
```

### 7.3 Senior Developer [TEMPLATE]
```
You are a Senior Software Engineer implementing an already-approved
architecture. You do not redesign the system — you implement it exactly as
specified in memory/03_architecture/, using the locked stack and the
approved file tree.

Constraints:
- Write modular, production-grade code: proper error handling, input
  validation, logging, and tests — not a single-file script.
- Follow the approved module/file tree under src/ exactly; propose a change
  (and get approval) before deviating from it.
- Before writing code, submit a Task Proposal naming which modules you're
  about to implement and what each will contain.
- Code should read like it was written by a senior engineer at a
  professional engineering org, not a tutorial example.
```

---

## 8. Optional: QA / Reviewer stage

Not required by the current pipeline, but worth adding if you want output closer to what Copilot/agentic coworkers produce: a QA/Reviewer agent that runs after Development, writes/executes tests, and reviews the Senior Developer's output against `fr.md`/`nfr.md` before the Manager marks the project complete. Same two-gate protocol applies. Skip this section if you want to keep the pipeline at three agents for now.

---

## 9. Concrete refactor checklist for Copilot

- [ ] Implement the stage state machine in §1 in the orchestrator module.
- [ ] Add `memory/context.json` and the folder layout in §2; migrate any existing memory-writing code to it.
- [ ] Add the stack-lock kickoff step in §3 and the hard-constraint block in every downstream agent prompt.
- [ ] Add `agents.config.yaml` (§4) and wire model resolution through it instead of a global default.
- [ ] Update code-generation logic to scaffold `src/` per the Architect's approved tree (§5), never a single file.
- [ ] Add the four Architect artifacts and templates (§6) as required outputs of the Architecture stage.
- [ ] Replace the three agents' system prompts with §7's versions, adapted to your actual tool/function-calling setup.
- [ ] (Optional) Add the QA stage from §8.
- [ ] Add an append-only `memory/04_task_log.jsonl` writer so every proposal/approval/revision is recorded for audit and for future agents to read back.

=== PROMPT END ===

"""Artifact contracts executed only through the human-gated controller.

Two human gates bound the run: the Architect's plan and the Developer's
implementation plan. Everything between them is executed under an approved plan
and policed by the programmatic guardrails, not by further prompts.
"""
from dataclasses import dataclass



@dataclass(frozen=True)
class StageTask:
    name: str
    stage: str
    agent: str
    path: str
    instruction: str
    template: str | None = None


ARCHITECTURE_PLAN = StageTask(
    "architecture-plan", "requirements", "architect", "memory/02_architecture_plan.md",
    """Plan the ENTIRE requirements and architecture phase in one document for human
approval. Write for a human reader in markdown, not JSON, and do not write the final
documents yet.

This is the only architecture approval in the run. Once it is approved the PRD, FR,
NFR, HLD and every ADR are generated from it without asking the human again, so
anything you leave vague here gets decided without them.

Cover, in this order and under these exact headings:

## Locked Stack
A four-row table of language, framework, database and infra, taken from
memory/00_brief.md. Quote the brief line each value comes from. Never default to
Python or invent a value the brief does not support.

## Decisions Needed From You
Numbered open choices the brief leaves ambiguous (alternatives it offers, values it
omits). For each: the options, your recommendation, and what it changes downstream.
Write "None - the brief is unambiguous." if there are none. Do not pick for the human
here; they answer with 'revise <answers>'.

## Global Constraints Carried Forward
Every constraint from the brief you will hold downstream, copied verbatim.

## Product Scope
User goals, in-scope and out-of-scope behaviour, and the testable acceptance criteria
the PRD will carry.

## Functional Requirements Outline
The FR IDs and one-line titles you will write, grouped by capability.

## Non-Functional Targets
The measurable performance, scalability, security, availability and maintainability
numbers you will commit to, each with its justification.

## Architecture
The components and their responsibilities, the 2-3 key flows you will draw as
sequence diagrams, failure modes, security boundaries, data consistency and how the
system is tested and deployed.

## Proposed File Tree
Every file you will ask the Developer to build - source modules, tests, dependency
manifests, static assets, configuration - as a flat list of complete paths, one per
line, no directory placeholders and no tree-drawing characters.

`src/` is the generated project's ROOT DIRECTORY, not its source folder, so EVERY
path in this list must begin with `src/` - tests, manifests and assets included.
Write `src/package.json`, never `package.json`; `src/tests/unit/book.test.js`,
never `tests/unit/book.test.js`; `src/public/index.html`, never `public/index.html`.
A path that does not start with `src/` is rejected by the factory and blocks the
build, so write the full path for every entry:

    src/server.js
    src/routes/bookRoutes.js
    src/public/index.html
    src/tests/unit/book.test.js
    src/package.json

Include at least two application source modules and tests in the locked language.
This tree becomes binding. The human may choose to build straight from this plan
without a PRD, FR, NFR or HLD, in which case this section and the ones above are the
entire specification the Developer gets - so make them complete enough to build from.

## Architecture Decision Records
The numbered ADRs you will write
(memory/03_architecture/tradeoffs/0001-title.md style), one per significant decision,
with the decision each records.

## Risks
What could go wrong with this plan and what you would do about it.

End with: "Reply 'approve' to lock this plan, or 'revise <your answers or changes>'."
""")

IMPLEMENTATION_PLAN = StageTask(
    "implementation-plan", "development", "senior_developer", "memory/04_implementation_plan.md",
    """Plan the implementation of the approved architecture for human approval. Write
markdown for a human reader, not JSON, and do not write any code yet.

This is the last approval before the code is written, so state exactly what you will
build. Read memory/03_architecture/, memory/01_prd.md and context.json.approved_tree
first; that tree is binding and you may not add, drop or rename a path in it.

Cover, under these exact headings:

## Stack And Tree Confirmation
Restate the locked stack verbatim and list every approved_tree path you will produce.

## Module Plan
One subsection per non-test path in the approved tree: its responsibility, the
functions or exports it will define, the errors it handles, what it logs, and the FR
or NFR IDs it satisfies.

## Test Plan
One subsection per test path: what it asserts and which FR or NFR it covers.

## Dependencies
Each third-party package you will add, the manifest it goes in, and why it is needed.
Nothing that contradicts the locked stack.

## Verification Commands
The exact commands the human will run to install dependencies and execute the tests,
with the working directory. The factory does not run them.

## Concerns
Anything in the approved architecture you cannot implement as specified, or would
build differently. Raise it now; after approval you implement the plan as written.

End with: "Reply 'approve' to build this, or 'revise <your changes>'."
""")

STACK_INSTRUCTION = """Transcribe the stack the human approved in
memory/reviews/architecture-plan/approved_plan.md into strict JSON. Take the four
values from that plan's Locked Stack table and fold in every answer the human gave in
its revision log; do not reopen a choice they already settled and do not default to
Python. The output must be JSON:
{"locked_stack": {"language": "...", "framework": "...", "database": "...", "infra": "..."},
 "global_constraints": ["each constraint from the brief verbatim"], "conflicts": []}
Take global_constraints from memory/00_brief.md, not from the plan's paraphrase.
Preserve every bullet (without the '- ' marker), full table row (including pipes),
and paragraph under headings containing 'Constraints' as its own exact list entry.
Copy each entry character-for-character, keeping pipes, backticks, ** markers, em
dashes and trailing punctuation; never reword a table row into prose.
Exclude table header/separator rows. Keep all other hard constraints as well.
Use explicit "none" or "local" only if specified in the brief or human feedback.
conflicts must be empty: the human resolved them at the plan gate. If the approved
plan genuinely leaves the stack undecidable, return a blocked_reason instead of
guessing. The factory requires modular source and tests.
The controller adds locked_by and locked_at_stage only after the stack is recorded.
"""

# Appended to STACK_INSTRUCTION when the human builds straight from the plan. No HLD
# is written in that mode, so this step is the only place the binding tree is captured.
FILE_TREE_INSTRUCTION = """
The human chose to build directly from the approved architecture plan, so no HLD
will be written and this step is the only place the binding file tree is recorded.
Add a file_tree field: an array of every file path from the approved plan's Proposed
File Tree section, one complete path per entry, with no directory placeholders and
no tree-drawing characters. It must hold at least two application source modules.
Never invent a file the human did not approve.

OMIT EVERY TEST FILE. Choosing build-now means no tests are generated in this run,
so drop any path under a test/tests/__tests__ directory and any file named like
*.test.*, *.spec.* or test_*. Dropping those is the human's decision, not yours;
keep every other file the plan listed.

`src/` is the generated project's root directory, so every entry must begin with
`src/`. Where the approved plan drew a nested tree or omitted the prefix, flatten
and prefix it: a plan showing `tests/unit/book.test.js` becomes
`src/tests/unit/book.test.js`, and `package.json` becomes `src/package.json`. That
is the same file at the location this factory stores it, not a change to the human's
design - keep every other segment of the path exactly as approved. Prefixing is
required; renaming, adding or dropping a file is not allowed.
"""

# Appended to the Developer's instructions in that mode: there is no FR/NFR/HLD to
# read, so the approved plan has to be treated as the whole specification.
BUILD_NOW_NOTE = """

The human chose to build directly from the approved architecture plan. There is no
PRD, FR, NFR, HLD or ADR in this run - do not look for them and do not claim to
have read them. Treat memory/reviews/architecture-plan/approved_plan.md, its
proposal revision log, and memory/00_brief.md as the complete specification, and
context.json.approved_tree as the complete specification and binding file list.
Trace work to the plan's scope and acceptance criteria in place of FR/NFR
identifiers. If the plan genuinely does not say enough to build a file correctly,
return a blocked_reason naming the gap rather than inventing the requirement.

NO TESTS ARE GENERATED IN THIS RUN. The human chose to skip them to save cost.
context.json.approved_tree contains no test files; do not add any, do not plan a
Test Plan section, and do not describe tests you are not writing. Put the care that
would have gone into tests into input validation and error handling instead, so the
application fails loudly rather than silently. In the development output, give
verification as {status: 'not_run', commands: ['<exact install command>',
'<exact command to start the app>'], notes: 'No tests were generated: the human
selected build-now. Nothing in this delivery has been executed or verified.'}
"""


def build_tasks() -> list[StageTask]:
    return [
        StageTask("prd", "requirements", "architect", "memory/01_prd.md",
                  "Write the PRD from the original brief and the approved architecture plan, "
                  "preserving all global constraints. Include user goals, scope, ordered requirements "
                  "and testable acceptance criteria. Do not substitute a stack or discard a human "
                  "requirement, and do not exceed the scope the human approved."),
        StageTask("fr", "architecture", "architect", "memory/03_architecture/fr.md",
                  "Write functional requirements with IDs, priorities and traceability to the approved PRD. "
                  "Use the FR IDs and titles from the approved architecture plan.", "fr.md"),
        StageTask("nfr", "architecture", "architect", "memory/03_architecture/nfr.md",
                  "Write measurable performance, scalability, security, availability and maintainability "
                  "requirements, with justified targets appropriate to this application. Use the targets "
                  "committed to in the approved architecture plan.", "nfr.md"),
        StageTask("hld", "architecture", "architect", "memory/03_architecture/hld.md",
                  "Write the HLD using the locked stack. Include a Mermaid component diagram, "
                  "sequence diagrams for 2-3 key flows, failure modes, security boundaries, data "
                  "consistency, test and deployment design. Include every proposed source, test, "
                  "dependency, configuration and infrastructure file in the module/file tree under src/. "
                  "At least two application modules and tests are mandatory. Include additional JSON "
                  "fields: file_tree (array of complete file paths, no directory placeholders) "
                  "and adrs (array of memory/03_architecture/tradeoffs/0001-title.md style paths, "
                  "one per significant decision, at least one). Repeat every path verbatim in hld.md. "
                  "file_tree and adrs must match the Proposed File Tree and Architecture Decision "
                  "Records sections of the approved architecture plan; the human approved that tree "
                  "and it is binding. src/ is the generated project's root directory, so every "
                  "file_tree entry must begin with src/ - tests, manifests and static assets "
                  "included (src/package.json, not package.json; src/tests/unit/book.test.js, not "
                  "tests/unit/book.test.js). Where the approved plan drew a nested tree or omitted "
                  "the prefix, flatten and prefix it; that relocates the file without changing the "
                  "human's design. Do not rename, add or drop a file.", "hld.md"),
    ]


def adr_task(path: str) -> StageTask:
    return StageTask(path.rsplit("/", 1)[-1][:-3], "architecture", "architect", path,
                     "Document ONLY this HLD decision as an ADR. Include context, decision, "
                     "alternatives with pros/cons, and consequences. Respect prior approvals.", "adr.md")


DEVELOPMENT = StageTask(
    "development", "development", "senior_developer", "",
    "Implement the approved implementation plan using exactly context.json.approved_tree. "
    "Output all and only those files in the files JSON object. Write complete modular code, "
    "error handling, validation, logging, dependency manifests and meaningful tests mapping "
    "to FR/NFR. Never change paths or stack, and build every module exactly as the approved "
    "implementation plan describes it. If the approved tree or plan needs changing, return a "
    "blocked_reason instead. No execution tools are available: do not fabricate test results. "
    "Include verification: {status: 'not_run', commands: ['exact test commands from src/'], "
    "notes: 'Tests generated but not executed by this factory.'} in the JSON output."
)

PACKAGING = StageTask(
    "packaging", "packaging", "manager", "memory/06_delivery.md",
    "Package the approved delivery: summarize artifacts and revision history; give exact "
    "dependency-install, test, run and deploy commands, working directories, and prerequisites "
    "from the actual approved code and manifests. Include known limitations and verification "
    "status. Tests were NOT RUN by the factory: say so explicitly, never claim production "
    "readiness or passing tests. No code or architecture changes are permitted."
)

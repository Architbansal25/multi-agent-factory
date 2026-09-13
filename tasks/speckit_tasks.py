"""CrewAI tasks implementing the manager-led delivery loop:

    Manager    -> instruction to Architect
    Architect  -> plan + PRD build steps for Developer
    Developer  -> implement (per service) -> self-test -> confirm to Architect
    Architect  -> check acceptance criteria -> confirm to Manager
    Manager    -> confirm delivery to the stakeholder

The pipeline scaffolds either a single application or two independent
microservices, depending on what ``services`` (see
``services/service_planner.py``) resolves to for the brief.
"""
from __future__ import annotations

from dataclasses import dataclass

from crewai import Agent, Task

from config.settings import Settings, settings as default_settings
from services.guardrails import code_guardrail
from services.service_planner import ServiceSpec


@dataclass(frozen=True)
class TaskPlan:
    """The ordered tasks plus the per-service implement tasks for post-processing."""

    tasks: list[Task]
    implement_tasks: list[tuple[Task, ServiceSpec]]


def _describe_services(services: list[ServiceSpec]) -> str:
    if len(services) == 1:
        return "a single application"
    names = ", ".join(f"'{svc.name}' (port {svc.port})" for svc in services)
    return f"{len(services)} independent microservices: {names}"


def build_tasks(
    *,
    manager: Agent,
    architect: Agent,
    developer: Agent,
    services: list[ServiceSpec],
    config: Settings | None = None,
) -> TaskPlan:
    """Create the ordered task pipeline. The brief is injected at kickoff via
    the ``{brief}`` template variable."""
    cfg = config or default_settings
    service_summary = _describe_services(services)

    kickoff = Task(
        description=(
            "Read the engineering brief below and write a clear build "
            "instruction addressed to the Software Architect. State what must "
            f"be built ({service_summary}), why it matters, and any hard "
            "constraints from the brief. Keep every service basic and simple.\n\n"
            "BRIEF:\n{brief}"
        ),
        expected_output=(
            "A short markdown 'Build Instruction' addressed to the Architect, "
            "covering scope, goals, and constraints."
        ),
        agent=manager,
        output_file=str(cfg.kickoff_path),
    )

    plan = Task(
        description=(
            "Read the Manager's build instruction and produce a lightweight "
            f"technical implementation plan covering {service_summary}. For each "
            "service, choose a single-file Python web stack (FastAPI with inline "
            "responses, or Streamlit for a UI), state the framework, the port it "
            "listens on, and how a caller/browser would exercise it. Keep every "
            "service basic - no database, no third-party integrations."
        ),
        expected_output=(
            "A markdown 'Implementation Plan' naming the framework, port, and "
            "endpoints/UI for each service."
        ),
        agent=architect,
        context=[kickoff],
        output_file=str(cfg.plan_path),
    )

    prd = Task(
        description=(
            "Using the plan, write a PRD-style, ordered set of build steps for "
            "the Developer, grouped by service if there is more than one. Each "
            "step must be concrete, independently checkable, and include the "
            "acceptance criteria the Developer's implementation will be judged "
            "against."
        ),
        expected_output=(
            "A markdown 'PRD' with ordered build steps and explicit acceptance "
            "criteria per service."
        ),
        agent=architect,
        context=[plan],
        output_file=str(cfg.prd_path),
    )

    implement_tasks: list[tuple[Task, ServiceSpec]] = []
    for service in services:
        implement = Task(
            description=(
                f"Follow the Architect's PRD to build '{service.name}' only. "
                "Output the COMPLETE source for a single runnable, basic Python "
                "service that matches the plan (FastAPI with inline responses, "
                f"or Streamlit for a UI). If it is a FastAPI service, it must run "
                f"on port {service.port} when started with uvicorn. Output ONLY "
                "raw Python source: no prose, no markdown fences."
            ),
            expected_output="A single, complete, syntactically valid Python source file.",
            agent=developer,
            context=[plan, prd],
            guardrail=code_guardrail,
            output_file=str(service.output_path),
        )
        implement_tasks.append((implement, service))

    developer_test = Task(
        description=(
            "Test each implementation you just built against the PRD's "
            "acceptance criteria (describe what you checked and the result for "
            "each service). Finish with an explicit sentence confirming to the "
            "Architect that the implementation(s) are ready for acceptance "
            "review."
        ),
        expected_output=(
            "A markdown test summary per service ending with an explicit "
            "readiness confirmation addressed to the Architect."
        ),
        agent=developer,
        context=[prd, *[t for t, _ in implement_tasks]],
    )

    architect_acceptance = Task(
        description=(
            "Check the Developer's implementation and test summary against the "
            "PRD's acceptance criteria for every service. State CONVERGED or NOT "
            "CONVERGED per service with a brief justification, then finish with "
            "an explicit sentence confirming to the Manager that the "
            "application is ready."
        ),
        expected_output=(
            "A markdown acceptance review stating CONVERGED or NOT CONVERGED per "
            "service, ending with an explicit readiness confirmation addressed "
            "to the Manager."
        ),
        agent=architect,
        context=[plan, prd, developer_test],
    )

    service_paths = "\n".join(
        f"- {svc.name}: `{svc.output_path}` (port {svc.port})" for svc in services
    )
    manager_signoff = Task(
        description=(
            "The Architect has confirmed the application is ready. Write the "
            "final delivery message to the stakeholder who requested this work. "
            "Start with the exact sentence 'The application is ready.' (or 'The "
            "applications are ready.' if there is more than one service). Then, "
            "using the plan to know which framework each service uses, give the "
            "exact copy-pasteable shell command to run each of the following "
            "services:\n"
            f"{service_paths}\n"
            "For a Streamlit service use `streamlit run <path>`. For a FastAPI "
            "service use `uvicorn <module.path>:app --reload --port <port>` "
            "(convert the file path to a dotted module path). List one command "
            "per service, clearly labeled, and close with 'Delivery flow "
            "complete.'"
        ),
        expected_output=(
            "A short final message starting with 'The application is ready.' (or "
            "'The applications are ready.'), a labeled, runnable command per "
            "service, and a closing 'Delivery flow complete.' line."
        ),
        agent=manager,
        context=[kickoff, architect_acceptance],
    )

    all_tasks = [
        kickoff,
        plan,
        prd,
        *[t for t, _ in implement_tasks],
        developer_test,
        architect_acceptance,
        manager_signoff,
    ]

    return TaskPlan(tasks=all_tasks, implement_tasks=implement_tasks)

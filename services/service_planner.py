"""Decides whether the brief calls for one application or two microservices."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from config.settings import Settings

# "two microservices", "2 services", "two separate services", etc.
_TWO_SERVICE_RE = re.compile(
    r"\b(two|2)\b[^.\n]{0,40}\b(microservices|micro-services|services|apps|applications)\b",
    re.IGNORECASE,
)
# "single service", "one application", "monolith", etc.
_SINGLE_SERVICE_RE = re.compile(
    r"\b(single|one|1|monolith(ic)?)\b[^.\n]{0,40}\b(service|application|app)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ServiceSpec:
    """A single deliverable service the crew must implement."""

    name: str
    slug: str
    port: int
    output_path: Path


def detect_services(brief: str, config: Settings) -> list[ServiceSpec]:
    """Inspect the brief text and decide the number of services to scaffold.

    Defaults to a single application unless the brief explicitly asks for two
    microservices/services.
    """
    if _TWO_SERVICE_RE.search(brief) and not _SINGLE_SERVICE_RE.search(brief):
        return [
            ServiceSpec(
                name="Service A",
                slug="service-a",
                port=8001,
                output_path=config.service_path("service-a"),
            ),
            ServiceSpec(
                name="Service B",
                slug="service-b",
                port=8002,
                output_path=config.service_path("service-b"),
            ),
        ]

    return [
        ServiceSpec(name="Application", slug="app", port=8000, output_path=config.app_path)
    ]

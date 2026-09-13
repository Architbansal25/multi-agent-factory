# Engineering Team Brief

<!--
This file is your input to the multi-agent engineering team.
Write your problem statement below and (optionally) fill in the other sections.
The CrewAI crew reads this whole file at kickoff. HTML comments like this one
are stripped automatically, so you can keep the guidance notes in place.

The virtual team runs a manager-led delivery loop:
  Engineering Manager -> reads this brief, instructs the Architect
  Software Architect  -> writes the technical plan + PRD build steps
  Senior Developer    -> implements (guardrailed) + self-tests, one per
                          service, then confirms readiness to the Architect
  Software Architect  -> checks acceptance criteria, confirms to the Manager
  Engineering Manager -> confirms "application is ready" + run instructions

By default a single application is built. To get TWO independent basic
microservices instead, mention it explicitly in the Problem Statement below,
e.g. "Build two microservices: ...". To be explicit about wanting one
application, say "single service"/"one application".
-->

## Problem Statement

<!-- Describe WHAT you want built and WHY. Avoid tech-stack details here. -->
Build a Book Library web application where users can add books, mark them as read or unread, filter the list by status, and view/manage individual book details.


## System Constraints

<!-- Hard requirements the team must respect. -->
- A Node.js + Express backend exposing a REST API.
- A JSON file acting as the data store (no database).
- A simple server-rendered or static HTML/CSS/vanilla-JS frontend consuming the API.

## Mandatory Tech Stack & Constraints
| Constraint | Rule |
|---|---|
| Runtime | Node.js |
| Web framework | **Must use Express.js** |
| Data store | JSON file on disk (e.g. `data/books.json`) — no external DB |
| Frontend JS | Vanilla JavaScript only |
| CSS frameworks | Bootstrap or Materialize **CSS only** — their bundled JS/JS components are **not allowed** |
| Styling | Plain CSS, Sass, or Less all permitted |
| Documentation | A `README.md` describing the app and local run steps is **required** |

Agents must not substitute a database (Mongo/Postgres/SQLite/etc.), a frontend framework (React/Vue/Angular), or Bootstrap/Materialize's JS widgets (modals, dropdowns, carousels via their JS bundle) — reimplement any needed interactivity in vanilla JS.


## Acceptance Criteria

<!-- How we know it is done. Keep these testable. -->
- Launching the app serves a page in the browser.
- The page prominently displays the application.
- The UI is clean and readable (aesthetic styling, centered content).

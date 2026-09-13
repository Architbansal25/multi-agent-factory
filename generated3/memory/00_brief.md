# Engineering Team Brief

<!--
This file is your input to the multi-agent engineering team.
Write your problem statement below and (optionally) fill in the other sections.
The original file is stored verbatim in memory/00_brief.md. Agents are told
to ignore HTML guidance comments like this one.

The run stops for you exactly twice. First the Architect plans the whole
requirements and architecture phase - the exact language/framework/database/
infra taken from this file, the choices it needs you to settle, the scope, the
requirements, the design, the binding file tree and the ADR list. Approving it
writes the PRD, FR, NFR, HLD and ADRs without asking again. Then the Developer
plans every module and test, and approving that builds the code and packages
the delivery. Use approve, revise <feedback>, or quit at either gate; revise as
many times as you need. Tests are generated, not executed. Source and shared
memory go under the selected project root.
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

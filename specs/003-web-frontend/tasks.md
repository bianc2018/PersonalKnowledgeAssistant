# Task Breakdown: 003-web-frontend

> Generated: 2026-04-10 | Source: [plan.md](./plan.md) + [spec.md](./spec.md) + [product-spec.md](./product-spec/product-spec.md)

---

## Phase A — Backend Foundation (Prerequisite)

**Goal:** Implement the attachment download API so the Knowledge Detail page can fully support file-based knowledge.

- [ ] **T-001** Implement `GET /api/knowledge/{item_id}/attachments/{attachment_id}/download` in `src/knowledge/router.py`
  - *AC:* Route accepts valid JWT, reads `attachments` table, decrypts file with `get_cached_master_key`, returns `StreamingResponse` with correct `Content-Type` and `Content-Disposition`.
  - *Covers:* FR-013, US-005

- [ ] **T-002** Write integration tests for attachment download API
  - *AC:* Happy path (decrypted stream + headers), 404 for missing attachment, 401 without token — all pass in `pytest`.
  - *Covers:* FR-013

- [ ] **T-003** Verify attachment download end-to-end via curl/browser
  - *AC:* Upload a PDF → open knowledge detail → click download → original file is returned intact.
  - *Covers:* US-005, FR-005

---

## Phase B — Frontend Infrastructure

**Goal:** Set up the SPA shell, routing, API client, SSE parser, and shared UI components.

- [ ] **T-004** Create `src/web/static/index.html` SPA shell with CDN dependencies
  - *AC:* HTML loads HTMX 2.0.8, Alpine.js 3.x, Tailwind CSS (Play CDN for dev), and bootstraps `app.js`.
  - *Covers:* FR-010

- [ ] **T-005** Implement `js/store.js` — minimal global state
  - *AC:* Stores `token`, `user`, `currentPage`, `toastQueue` with reactive Alpine integration where needed.
  - *Covers:* FR-001

- [ ] **T-006** Implement `js/api.js` — centralized fetch wrapper
  - *AC:* All API calls prefixed with `/api`, attach `Authorization: Bearer <token>`, auto-intercept 401 and redirect to `#/login` with toast, support JSON and FormData.
  - *Covers:* FR-001, FR-006, FR-007

- [ ] **T-007** Implement `js/router.js` — hash router
  - *AC:* Maps `#/login`, `#/dashboard`, `#/knowledge`, `#/chat`, `#/research`, `#/settings` and unknown hashes to fallback; guards protected routes.
  - *Covers:* FR-010

- [ ] **T-008** Implement `js/sse.js` — `fetch + ReadableStream` SSE parser
  - *AC:* Opens fetch with Bearer header, reads stream line-by-line, dispatches events (`delta`, `citation`, `done`, `error`, `status`, `progress`, `chunk`, `question`, `report`) to callbacks; supports abort.
  - *Covers:* FR-006, FR-007

- [ ] **T-009** Implement `js/ui.js` — shared UI helpers
  - *AC:* Provides `showToast(message, type)`, `showModal(title, content, actions)`, skeleton render/remove, and a lightweight client-side markdown renderer.
  - *Covers:* FR-011

---

## Phase C — Page-by-Page UI Implementation

**Goal:** Build each page, testing against the live backend as we go.

### C.1 Auth Pages

- [x] **T-010** Implement Login / Init pages (`pages/login.js`, `pages/init.js`)
  - *AC:* First visit shows init form (password ≥8, letter+number); later visits show login; successful auth stores JWT and redirects to `#/dashboard`; supports "remember me".
  - *Covers:* US-001, FR-001

### C.2 Dashboard

- [x] **T-011** Implement Dashboard page (`pages/dashboard.js`)
  - *AC:* Calls `/api/system/status`, displays knowledge count, LLM/Embedding/Search status badges, recent knowledge cards (up to 5), recent conversation shortcuts (up to 3), and quick action buttons.
  - *Covers:* US-002, FR-002

### C.3 Knowledge Base

- [x] **T-012** Implement Knowledge List page (`pages/knowledge.js` — list view)
  - *AC:* Fetches `/api/knowledge` with pagination (20/page), search query, and tag filters; displays cards with title, summary, tags, confidence badge, creation time; supports pagination controls.
  - *Covers:* US-003, FR-003

- [x] **T-013** Implement Knowledge Create/Edit flows
  - *AC:* "Add text" modal/form → `POST /api/knowledge`; "Upload file" → `POST /api/knowledge/upload` with progress indicator; "Add URL" → `POST /api/knowledge/url`; inline validation for content length ≥5 chars.
  - *Covers:* US-004, FR-004

- [x] **T-014** Implement Knowledge Detail page
  - *AC:* Displays full content (markdown rendered), editable tags, attachment list with working download links (T-001), confidence score + rationale, version timeline; editing opens a form that calls `PATCH /api/knowledge/{id}`.
  - *Covers:* US-005, FR-005

### C.4 Chat

- [x] **T-015** Implement Chat page shell (`pages/chat.js` — layout + sidebar)
  - *AC:* Left sidebar lists conversations with new/rename/delete actions; center area shows selected conversation header.
  - *Covers:* US-006, FR-006

- [x] **T-016** Implement Chat message thread and history loading
  - *AC:* Loads messages via `GET /api/chat/conversations/{id}/messages`; renders user/assistant bubbles; handles new conversation creation on first message.
  - *Covers:* US-006, FR-006

- [x] **T-017** Implement Chat SSE streaming and citation rendering
  - *AC:* Sending a message calls `POST .../messages?stream=true`; uses `sse.js` to Append deltas in real time; renders `citation` events as clickable chips that open a tooltip/modal with source summary.
  - *Covers:* US-006, FR-006

### C.5 Research

- [x] **T-018** Implement Research List page (`pages/research.js` — list view)
  - *AC:* Displays task cards with status badges (queued/running/awaiting_input/completed/error), pagination, and a "New Research" button opening a form.
  - *Covers:* US-007, FR-007

- [x] **T-019** Implement Research Detail page — SSE progress and decision interaction
  - *AC:* Opens SSE stream for task events; renders progress updates and chunks; when `question` event arrives, pauses and shows a decision form; on submit calls `POST /api/research/{task_id}/respond`; displays markdown report on completion.
  - *Covers:* US-007, FR-007

- [x] **T-020** Implement "Save report to knowledge base" flow
  - *AC:* On `report` event completion, shows "Save to Knowledge Base" button; click calls `POST /api/research/{task_id}/save`; success shows toast and optionally redirects to knowledge detail.
  - *Covers:* US-008

### C.6 Settings

- [x] **T-021** Implement Settings forms — LLM, Embedding, Search, Privacy, Storage
  - *AC:* Loads current config via `GET /api/system/config`; editable sections for LLM URL/key/model, Embedding settings, Search API, three privacy toggles, version retention policy; saves via `PUT /api/system/config` with success toast.
  - *Covers:* US-009, FR-008

- [x] **T-022** Implement Export / Import / Reset interactions
  - *AC:* Export triggers `POST /api/system/export` and uses `Blob` + `URL.createObjectURL` to download ZIP; Import accepts ZIP file via `POST /api/system/import` and shows result summary; Reset opens a confirmation modal requiring password.
  - *Covers:* US-009, FR-009

---

## Phase D — Responsive & Polish

**Goal:** Ensure the UI works on smaller screens and meets NFRs.

- [ ] **T-023** Add responsive layout adaptations
  - *AC:* Sidebar collapses into a hamburger drawer on screens < 768px; grids switch to single column; input buttons have min touch target 44×44.
  - *Covers:* US-010, FR-012

- [ ] **T-024** Accessibility manual spot-check
  - *AC:* All interactive elements reachable via Tab; focus rings visible; forms have `<label>`; AI new messages use `aria-live="polite"`; no keyboard traps detected.
  - *Covers:* NFR Accessibility

- [ ] **T-025** Performance spot-check
  - *AC:* DevTools shows `DOMContentLoaded` ≤2s on local network; API list TTFB ≤500ms; search input debounced.
  - *Covers:* NFR Performance

---

## Phase E — Integration QA & Bug Fix

**Goal:** Run manual end-to-end QA and fix any P0/P1 issues before completion.

- [ ] **T-026** Run E2E-001: First-time user complete journey
  - *AC:* Init → Login → Add knowledge → Chat question → Receive streaming cited answer. All steps pass without console errors or blocking bugs.
  - *Covers:* TC-E2E-001

- [ ] **T-027** Run E2E-002: Research task complete lifecycle
  - *AC:* Submit topic → SSE progress OK → Answer decision → Save report → Report appears in knowledge base and is quotable in Chat.
  - *Covers:* TC-E2E-002

- [ ] **T-028** Run E2E-003: Post-restart recovery experience
  - *AC:* Log in → restart backend → perform any action → frontend catches 401 → shows toast → redirects to login → after re-login, user can resume.
  - *Covers:* TC-E2E-003

- [ ] **T-029** Fix any P0/P1 issues discovered in Phase E
  - *AC:* All checklist items from T-026~T-028 pass; no blocking bugs remain.

---

## Optional / Should Have (Post-MVP)

- [ ] **T-030** Bulk operations in Knowledge List (multi-select + bulk tag/delete)
  - *Covers:* US-011, FR-013

- [ ] **T-031** Keyboard shortcuts (`/` for search, `Cmd/Ctrl+K` command palette)
  - *Covers:* US-012

- [ ] **T-032** Dark mode theme toggle
  - *Covers:* US-013

---

## Task Statistics

| Metric | Count |
|--------|-------|
| Total tasks (Must/Should MVP) | 29 |
| Backend tasks | 3 |
| Frontend infra tasks | 6 |
| Page implementation tasks | 13 |
| Polish & QA tasks | 7 |
| Optional post-MVP tasks | 3 |

## Traceability Matrix

| Must Have Story | Covered by Tasks |
|-----------------|------------------|
| US-001 Login/Init | T-004, T-005, T-006, T-010 |
| US-002 Dashboard | T-011 |
| US-003 Knowledge browse | T-012 |
| US-004 Add/edit knowledge | T-013 |
| US-005 Knowledge detail | T-001, T-002, T-003, T-014 |
| US-006 Chat | T-008, T-015, T-016, T-017 |
| US-007 Research | T-008, T-018, T-019 |
| US-008 Save report | T-020 |
| US-009 Settings | T-021, T-022 |

| Functional Requirement | Covered by Tasks |
|------------------------|------------------|
| FR-001 Auth/Init | T-010 |
| FR-002 Dashboard status | T-011 |
| FR-003 Knowledge search/filter | T-012 |
| FR-004 Knowledge create/upload/URL | T-013 |
| FR-005 Knowledge detail + download | T-001~T-003, T-014 |
| FR-006 Chat + SSE | T-008, T-015~T-017 |
| FR-007 Research + SSE | T-008, T-018~T-020 |
| FR-008 Settings config | T-021 |
| FR-009 Export/Import/Reset | T-022 |
| FR-010 Hash routing | T-004, T-007 |
| FR-011 Visual feedback | T-009 |
| FR-012 Responsive | T-023 |
| FR-013 Attachment download API | T-001~T-003 |

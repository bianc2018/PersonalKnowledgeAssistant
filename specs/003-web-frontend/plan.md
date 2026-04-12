# Technical Plan: Web 前端页面开发

> Feature: `003-web-frontend` | Date: 2026-04-10
> Spec: [spec.md](./spec.md) | Codebase analysis: [research/codebase-analysis.md](./research/codebase-analysis.md)

---

## 1. Architecture Overview

### 1.1 High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (Client)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Jinja2 Shell │  │  HTMX + Alpine │  │ Tailwind CSS    │  │
│  │ (index.html) │  │  (interactivity)│  │ (styling)       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│            │                  │                  │          │
│            └──────────────────┼──────────────────┘          │
│                               │ hash routing                 │
│                    ┌──────────┴──────────┐                  │
│                    │    Vanilla JS SPA   │                  │
│                    │  (mounted in /static) │                 │
│                    └──────────┬──────────┘                  │
└───────────────────────────────┼─────────────────────────────┘
                                │ fetch / SSE ReadableStream
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                FastAPI (Existing Backend)                   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ /api/auth  │ │ /api/system│ │ /api/chat  │ │/api/research│
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  NEW: /api/knowledge/{id}/attachments/{attachment_id}/  ││
│  │                        /download                        ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Key Principles

1. **Zero Node dependency**: All frontend assets are static files served by FastAPI's `StaticFiles`.
2. **Hash routing**: All client-side navigation uses `location.hash` (`#/login`, `#/knowledge`, etc.) to avoid backend catch-all routes.
3. **Bearer JWT for all protected APIs**: The token is read from `sessionStorage`/`localStorage` and attached to every `fetch` call.
4. **Manual SSE parsing**: Chat and Research SSE endpoints are consumed via `fetch + ReadableStream` so the `Authorization: Bearer <token>` header can be sent without backend modifications.
5. **Backend-first for attachment download**: The attachment download API must be implemented before Knowledge Detail UI can be considered complete.

---

## 2. Data Model

### 2.1 Changes

**No new database tables** are introduced for the frontend.

**One new backend route** is required:

| Route | Method | Description |
|-------|--------|-------------|
| `/api/knowledge/{item_id}/attachments/{attachment_id}/download` | GET | Decrypts the file using `get_cached_master_key(token)` and returns a `StreamingResponse` with the correct `Content-Type` and `Content-Disposition: attachment; filename="..."`. |

### 2.2 Route Implementation Details

File: `src/knowledge/router.py`

Pseudo-code:

```python
@router.get("/{item_id}/attachments/{attachment_id}/download")
async def download_attachment(
    item_id: UUID,
    attachment_id: UUID,
    user: User = Depends(get_current_user),
):
    attachment = await get_attachment(item_id, attachment_id)
    if not attachment or attachment.storage_path is None:
        raise HTTPException(404)
    master_key = get_cached_master_key(user.token)  # or derive logic
    decrypted_stream = decrypt_file_stream(attachment.storage_path, master_key)
    return StreamingResponse(
        decrypted_stream,
        media_type=attachment.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{attachment.filename}"'}
    )
```

- Reuses existing `Attachment` schema fields: `filename`, `mime_type`, `storage_path`.
- Must reuse the project's existing AES-256-GCM decryption helper (likely in `src/auth/service.py` or `src/utils.py`).

---

## 3. Frontend Structure

### 3.1 Directory Layout

```
src/web/
├── static/
│   ├── index.html              # SPA entrypoint (Jinja2 template shell)
│   ├── css/
│   │   └── app.css             # Tailwind pre-compiled output (single file)
│   └── js/
│       ├── app.js              # Bootstrap: init router, auth state, global error handling
│       ├── api.js              # Centralized fetch wrapper (auth headers, base URL, JSON/FormData)
│       ├── router.js           # Hash router: map #/path → page render function
│       ├── sse.js              # fetch + ReadableStream SSE parser for Chat & Research
│       ├── store.js            # Minimal global state (currentUser, currentPage, toast queue)
│       ├── ui.js               # Shared UI helpers (toast, modal, skeleton, markdown render)
│       └── pages/
│           ├── init.js         # System initialization (first-use password setup)
│           ├── login.js        # Login form
│           ├── dashboard.js    # Dashboard cards and quick actions
│           ├── knowledge.js    # Knowledge list + detail + create/edit modal
│           ├── chat.js         # Conversation sidebar + streaming message thread
│           ├── research.js     # Research task list + detail + SSE progress
│           └── settings.js     # Config forms + export/import/reset
└── templates/
    └── index.html              # Fallback Jinja2 template if needed (optional)
```

### 3.2 Core Modules

#### `router.js` — Hash Router

```javascript
const routes = {
  '': () => redirectTo('#/dashboard'),
  'login': renderLogin,
  'dashboard': renderDashboard,
  'knowledge': renderKnowledge,
  'knowledge/:id': renderKnowledgeDetail,
  'chat': renderChat,
  'chat/:id': renderChatConversation,
  'research': renderResearch,
  'research/:id': renderResearchDetail,
  'settings': renderSettings,
};
```

- On `hashchange`, parse the path and call the matching renderer.
- Before rendering any protected route, check `store.token`; if missing, redirect to `#/login`.

#### `api.js` — Fetch Wrapper

Responsibilities:
- Prefix all paths with `/api`.
- Attach `Authorization: Bearer ${store.token}` for protected routes.
- Handle 401 globally: clear token, redirect to `#/login` with a toast message.
- Return parsed JSON or `Response` object for binary downloads.

Key functions:
- `apiGet(path, params)`
- `apiPost(path, body)`
- `apiPatch(path, body)`
- `apiDelete(path)`
- `apiUpload(path, formData)` — returns upload progress if supported.
- `apiExport(path, body)` — returns `Blob` for ZIP download.

#### `sse.js` — Manual SSE Stream Parser

Responsibilities:
- Open a `fetch` request with `Authorization` header.
- Read the response body as a `ReadableStream`.
- Parse `data:` lines and dispatch events by type: `delta`, `citation`, `done`, `error` (Chat) or `status`, `progress`, `chunk`, `question`, `report`, `error` (Research).
- Provide callbacks: `onEvent(type, payload)`, `onError(err)`, `onClose()`.
- Support caller-initiated abort via `AbortController`.

#### `ui.js` — Shared UI Helpers

- `showToast(message, type = 'info')` — auto-dismiss after 3s.
- `showModal(title, contentHtml, actions)` — Alpine-powered modal.
- `renderSkeleton(container)` / `removeSkeleton(container)`.
- `renderMarkdown(mdText)` — lightweight client-side markdown → HTML (e.g., marked.js CDN or a minimal custom parser).

---

## 4. Backend Changes

### 4.1 Attachment Download Route

**File:** `src/knowledge/router.py`
**New function:** `download_attachment`
**Tests:** `tests/integration/test_knowledge.py` (or new file)

Test cases:
- Happy path: valid item_id + attachment_id, decrypted stream returned with correct headers.
- 404: attachment does not exist.
- 401/403: missing or invalid token.

### 4.2 Main.py Adjustments (Optional)

**File:** `src/main.py`

Current root handler (`/`) returns `index.html` from `static_dir`. No changes are strictly required because hash routing avoids history-mode refresh issues. However, verify that `static_dir / "index.html"` exists after frontend files are added.

---

## 5. Implementation Phases

### Phase A — Backend Foundation (Prerequisite)

**Goal:** Implement the attachment download API so the Knowledge Detail page can be fully functional.

**Tasks:**
1. Add `GET /api/knowledge/{item_id}/attachments/{attachment_id}/download` to `src/knowledge/router.py`.
2. Reuse decryption logic from auth/utils.
3. Write integration tests.
4. Verify the route works via curl/manual browser download.

### Phase B — Frontend Infrastructure

**Goal:** Set up the SPA shell, routing, API client, SSE parser, and shared UI components.

**Tasks:**
1. Create `src/web/static/index.html` with Jinja2 base layout.
2. Add CDN links: HTMX 2.0.8, Alpine.js 3.x, Tailwind Play CDN (dev) or precompiled `app.css` (prod).
3. Implement `js/store.js`, `js/api.js`, `js/router.js`, `js/sse.js`, `js/ui.js`.
4. Implement global 401 interceptor and toast system.
5. Add `js/app.js` bootstrapping logic.

### Phase C — Page-by-Page UI Implementation

Order of implementation (each page tested against live backend as it's built):

1. **Login / Init (`pages/login.js`, `pages/init.js`)**
   - Password validation UI.
   - JWT storage logic.
   - Redirect after authentication.

2. **Dashboard (`pages/dashboard.js`)**
   - Fetch `/api/system/status`.
   - Render stat cards and quick links.
   - Empty state for first-time users.

3. **Knowledge List & Detail (`pages/knowledge.js`)**
   - List: search, tag filters, pagination, soft-delete toggle.
   - Create: text form, file upload, URL form.
   - Detail: content viewer, tag editor, attachment list with download links, confidence badge, version timeline.

4. **Chat (`pages/chat.js`)**
   - Sidebar: conversation list, new/rename/delete.
   - Thread: message history loader.
   - Input: send message, trigger SSE stream, render deltas and citations.
   - Citation chip hover/click behavior.

5. **Research (`pages/research.js`)**
   - List: status badges, pagination.
   - New task form.
   - Detail: SSE progress renderer, decision question form, report preview, save-to-knowledge button.

6. **Settings (`pages/settings.js`)**
   - Forms grouped by category.
   - Export (blob download), Import (file upload + result modal), Reset (password confirmation modal).

### Phase D — Responsive & Polish

**Goal:** Ensure the UI works on smaller screens and meets NFRs.

**Tasks:**
1. Add responsive CSS breakpoints for sidebar collapse.
2. Verify touch targets ≥44px for buttons and inputs.
3. Keyboard navigation spot-check (Tab order, focus rings).
4. Performance spot-check (DevTools Network tab, Lighthouse).

### Phase E — Integration QA

**Goal:** Run end-to-end manual QA of all Must Have stories.

**Tasks:**
1. Walk through TC-E2E-001, TC-E2E-002, TC-E2E-003 (from spec.md).
2. Run backend integration tests (attachment download).
3. Document any P0/P1 issues and fix before Phase 6 completion.

---

## 6. Testing Specification

### 6.1 Backend Tests

- **Integration test file:** `tests/integration/test_knowledge_attachment_download.py`
- Coverage target: ≥80% for new route logic.
- Cases:
  1. Download decrypted file with correct `Content-Disposition`.
  2. 404 for non-existent attachment.
  3. 401 without token; 401 with expired/revoked token.

### 6.2 Frontend Testing

No automated E2E framework in v1. Testing is manual + script-assisted:

| Checklist | Method |
|-----------|--------|
| All hash routes render without JS errors | Manual navigation |
| 401 interceptor triggers correctly | Restart backend, then click any action |
| Chat SSE streams 10 consecutive messages without interruption | Manual QA |
| Research SSE shows progress + decision form + final report | Manual QA |
| File upload → detail page → download completes the loop | Manual QA |
| Export ZIP triggers browser download | Manual QA |
| Import ZIP shows result summary | Manual QA |
| Reset with wrong password is blocked | Manual QA |
| Reset with correct password succeeds and redirects to init | Manual QA |

---

## 7. Performance & Security

### 7.1 Performance Targets

| Target | Measurement | How to achieve |
|--------|-------------|----------------|
| First paint ≤2s | DevTools Performance | Single CSS file, no render-blocking JS, minimal DOM size on login |
| API TTFB ≤500ms | DevTools Network | Backend already optimized; frontend debounce search input |
| Chat SSE latency ≤1s first delta | Stopwatch / DevTools | Stream parsing overhead is negligible |

### 7.2 Security Checklist

- Password never stored client-side.
- JWT in `sessionStorage` by default; `localStorage` only when "remember me" is checked.
- `api.js` intercepts 401 and clears stored tokens immediately.
- Export/Import/Reset require correct password confirmation.
- XSS prevention: UI helpers must escape HTML when rendering user-generated content; Markdown renderer should sanitize raw HTML.

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Attachment download API decryption fails due to missing key helper exposure | High | Verify decryption util is importable from `knowledge` router; if not, refactor auth utils to expose a safe wrapper |
| HTMX + Alpine.js interaction bugs (e.g., Alpine state lost after HTMX swap) | Medium | Use Alpine `x-data` on persistent containers; prefer Alpine for client-only UI and HTMX for server-driven fragments |
| SSE fetch stream lacks retry logic, causing user-visible dropouts | Medium | Build retry counter (max 3) with exponential backoff in `sse.js`; show UI banner when retry exhausted |
| Soft-deleted knowledge items still visible in Chat citations but not in list | Low | Design decision — ensure soft-deleted items are fetched by ID for citation display |

---

## 9. Open Design Questions

1. **Citation precision:** v1 renders citation as a clickable chip referencing the `KnowledgeItem` title + summary. No sentence-level highlighting.
2. **Knowledge list default sort:** Time descending (most recently created first).
3. **Mobile nav:** Sidebar collapses into a hamburger drawer on screens < 768px; no dedicated bottom tab bar in v1.

---

## 10. Definition of Done

This technical plan is considered satisfied when:

1. Attachment download API is merged with passing integration tests.
2. All Must Have pages (Login, Dashboard, Knowledge, Chat, Research, Settings) are renderable and manually QA-verified.
3. Hash routing works across all views without 404 on refresh.
4. No P0 or P1 blocking bugs remain in the manual QA checklist.
5. `plan.md` traceability to `spec.md` and `product-spec.md` is maintained (no missing Must Have stories).

# LangGraph Migration Plan — 5 Phases

**Created:** 2026-03-16  
**Status:** Ready to Start  
**Estimated Effort:** Large (5 phases, ~60-80 development hours)

## Project Overview

Migrate the career-flow AI resume tailoring app from manual `asyncio.gather` pipeline orchestration to LangGraph with:
- Human-in-the-loop (HITL) interrupts for review committee approval
- Real-time streaming progress via SSE
- Chat-first UI (ChatGPT-style with artifacts)
- Session persistence and history (SQLite)
- Backward compatibility with existing "Quick Generate" flow

**Architecture Decisions (Locked):**
- LangGraph = orchestration layer (state, branching, checkpoints, HITL)
- pydantic-ai = stays as LLM interaction layer (agents become leaf nodes)
- SSE = transport for streaming (FastAPI StreamingResponse + graph.astream())
- SQLite = persistence (langgraph-checkpoint-sqlite)
- No LangChain, No PostgreSQL, No Docker
- Preserve anti-hallucination safety (deterministic validator + AI checker)

---

## Phase 1: LangGraph Core Migration (Pure Refactor)

**Goal:** Replace `backend/app/agents/pipeline.py` with LangGraph StateGraph. Identical external behavior.

### Implementation Tasks

- [x] **P1.1: Add dependencies and test harness**
  - Update `backend/pyproject.toml`: add `langgraph`, `pytest`, `pytest-asyncio`, `httpx`
  - Create `backend/tests/conftest.py` with FastAPI test client fixtures
  - Create `backend/tests/fixtures/` for mock data (resume, JD, expected CV outputs)
  - Create `backend/tests/graph/test_generation_graph.py` skeleton
  - Create `backend/tests/api/test_generate_api.py` skeleton
  - Run `poetry install` and verify pytest works
  - **Verification:** `cd backend && poetry run pytest --collect-only`

- [x] **P1.2: Write regression tests for current pipeline**
  - In `backend/tests/api/test_generate_api.py`, test current `/api/generate`:
    - Standard mode (review_mode=false): tailor → validate
    - Review mode (review_mode=true): full pipeline with reviewers
    - Response schema matches current `GenerateResponse`
  - In `backend/tests/graph/test_generation_graph.py`, prepare test cases for graph behavior:
    - Successful standard path
    - Successful review path
    - Reviewer failure (one fails, others succeed)
    - Zero successful reviewers (skip synthesis)
  - Mock all LLM calls (pydantic-ai agents)
  - **Verification:** `poetry run pytest backend/tests/api/test_generate_api.py -v` (should pass against current code)

- [x] **P1.3: Create LangGraph state schema**
  - Create `backend/app/graph/__init__.py`
  - Create `backend/app/graph/state.py` with `GenerationState` TypedDict:
    ```python
    class GenerationState(TypedDict, total=False):
        request_id: str
        resume_text: str
        job_description: str
        user_instructions: str | None
        review_mode: bool
        run_hallucination_check: bool
        draft_cv: CV | None
        current_cv_dict: dict[str, Any] | None
        reviews: Annotated[list[ReviewMemo], operator.add]
        review_errors: Annotated[list[dict[str, str]], operator.add]
        hallucination_report: HallucinationReport | None
        review_panel: ReviewPanelResult | None
        validation_result: dict[str, Any] | None
        final_response: dict[str, Any] | None
    ```
  - Import `Annotated` from `typing`, `operator` from stdlib
  - **Verification:** `from backend.app.graph.state import GenerationState` works

- [x] **P1.4: Create runtime config for secrets**
  - Create `backend/app/graph/runtime.py` with `GraphRuntimeConfig` dataclass:
    ```python
    @dataclass
    class GraphRuntimeConfig:
        model_name: str
        api_key: str
        review_model_name: str | None = None
        review_api_key: str | None = None
    ```
  - **Verification:** `from backend.app.graph.runtime import GraphRuntimeConfig` works

- [x] **P1.5: Create node wrappers for existing agents**
  - Create `backend/app/graph/nodes_generation.py`
  - Implement async node functions:
    - `tailor_node(state: GenerationState, config: RunnableConfig) -> dict`
    - `hr_review_node(state: GenerationState, config: RunnableConfig) -> dict`
    - `technical_review_node(state: GenerationState, config: RunnableConfig) -> dict`
    - `ats_review_node(state: GenerationState, config: RunnableConfig) -> dict`
    - `hallucination_check_node(state: GenerationState, config: RunnableConfig) -> dict`
    - `synthesis_node(state: GenerationState, config: RunnableConfig) -> dict`
    - `validate_node(state: GenerationState, config: RunnableConfig) -> dict`
  - Each node:
    - Extracts runtime config via `config["configurable"]["runtime"]`
    - Calls existing pydantic-ai agent from `backend/app/agents/*.py`
    - Catches exceptions and writes to `review_errors` for reviewer nodes
    - Returns dict with state updates
  - **Verification:** Import nodes, inspect signatures

- [x] **P1.6: Build the generation graph**
  - Create `backend/app/graph/build_generation_graph.py`
  - Implement `build_generation_graph() -> StateGraph`:
    - Add all nodes from nodes_generation.py
    - Add conditional edge after `tailor`:
      - `review_mode=false` → `validate`
      - `review_mode=true` → fan-out to `hr_review`, `technical_review`, `ats_review`
    - Add conditional edge for hallucination check (if enabled)
    - Add `review_join` node that waits for all parallel reviewers (defer=True)
    - Add conditional edge after `review_join`:
      - If any reviews exist → `synthesis`
      - If zero reviews → `validate`
    - Add edge from `synthesis` → `validate`
    - Set `tailor` as entry point
    - Set `validate` as END
  - **Verification:** `graph = build_generation_graph(); graph.get_graph().draw_mermaid()` renders

- [x] **P1.7: Create graph registry and compilation**
  - Create `backend/app/graph/registry.py`
  - Implement `get_generation_graph(checkpointer=None) -> CompiledGraph`:
    - Use `InMemorySaver()` as default checkpointer (SQLite comes in Phase 5)
    - Return compiled graph
  - **Verification:** `graph = get_generation_graph(); assert graph is not None`

- [x] **P1.8: Refactor pipeline.py to use LangGraph**
  - Open `backend/app/agents/pipeline.py`
  - Refactor `generate_cv_standard(...)`:
    - Call `get_generation_graph()`
    - Build `GenerationState` from inputs
    - Build `GraphRuntimeConfig` from model/api_key args
    - Invoke: `result = await graph.ainvoke(state, config={"configurable": {"thread_id": request_id, "runtime": runtime_config}})`
    - Extract `final_response` from result state
    - Return same dict shape as current implementation
  - Refactor `generate_cv_with_review(...)` similarly
  - **Verification:** `lsp_diagnostics` clean, existing tests pass

- [x] **P1.9: Run full test suite and verify API contract**
  - Run `poetry run pytest backend/tests/graph/ backend/tests/api/`
  - All tests should pass
  - Manual smoke test: `curl -X POST http://localhost:8000/api/generate` with sample data
  - Compare response to current implementation (should be identical)
  - **Verification:** All tests green, API response unchanged

### Atomic Commits (Phase 1)
1. `test(backend): add pytest harness and generation pipeline regression tests`
2. `feat(backend): add langgraph generation state, runtime config, and node wrappers`
3. `refactor(backend): route pipeline facade through compiled langgraph graph`

### Acceptance Criteria (Phase 1)
- [ ] `cd backend && poetry run pytest tests/graph/test_generation_graph.py tests/api/test_generate_api.py` passes
- [ ] `lsp_diagnostics` shows zero errors at project level
- [ ] `curl -X POST http://localhost:8000/api/generate` returns identical schema to pre-migration

---

## Phase 2: SSE Streaming + Progress UI

**Goal:** Add real-time pipeline progress streaming alongside existing blocking endpoint.

### Implementation Tasks

- [x] **P2.1: Add frontend test tooling**
  - Update `apps/web/package.json`: add `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`
  - Create `apps/web/vitest.config.ts`
  - Create `apps/web/src/test/setup.ts`
  - **Verification:** `cd apps/web && pnpm test -- --version`

- [x] **P2.2: Create backend streaming event helpers**
  - Create `backend/app/graph/events.py`
  - Implement helper functions around `get_stream_writer()`:
    - `emit_run_started(writer, thread_id, review_mode)`
    - `emit_step_started(writer, step_name)`
    - `emit_step_completed(writer, step_name)`
    - `emit_review_memo(writer, reviewer_role, memo)`
    - `emit_review_failed(writer, reviewer_role, error)`
    - `emit_validation_completed(writer, ats_issues, hallucination_warnings)`
    - `emit_result(writer, response)`
    - `emit_error(writer, message)`
    - `emit_run_completed(writer, thread_id, status)`
  - **Verification:** Import helpers, inspect signatures

- [x] **P2.3: Update graph nodes to emit progress events**
  - Update `backend/app/graph/nodes_generation.py`:
    - Each node calls `get_stream_writer()` from config
    - Emit `step_started` at beginning
    - Emit `step_completed` at end
    - Reviewer nodes emit `review_memo` or `review_failed`
    - Validate node emits `validation_completed`
  - **Verification:** `lsp_diagnostics` clean

- [x] **P2.4: Create SSE streaming endpoint**
  - Create `backend/app/api/sse.py`
  - Implement SSE formatter: `format_sse(event: str, data: dict) -> str`
  - Implement async generator: `stream_generation(state, config, graph)`
    - Wraps `graph.astream(state, config, stream_mode=["custom", "updates"])`
    - Formats events as SSE frames
    - Yields `data: {json}\n\n` format
  - Add route to `backend/app/api/generate.py`:
    - `POST /api/generate/stream`
    - Request body same as `/api/generate` plus optional `thread_id`
    - Returns `StreamingResponse(stream_generation(...), media_type="text/event-stream")`
  - **Verification:** `lsp_diagnostics` clean, route registered

- [x] **P2.5: Write backend streaming tests**
  - Create `backend/tests/api/test_generate_stream_api.py`
  - Test SSE endpoint:
    - Events arrive in correct order
    - All expected events present (run.started → steps → result → run.completed)
    - Reviewer memos included in review mode
    - Final result matches blocking endpoint output
  - Create `backend/tests/graph/test_stream_events.py`
  - Test node event emission with mocked stream writer
  - **Verification:** `poetry run pytest backend/tests/api/test_generate_stream_api.py backend/tests/graph/test_stream_events.py -v`

- [x] **P2.6: Create frontend SSE client**
  - Create `apps/web/src/lib/sse.ts`
  - Implement `parseSSE(response: Response, handlers: EventHandlers): Promise<void>`
    - Uses `fetch()` for POST body support (EventSource doesn't support POST)
    - Parses `text/event-stream` format
    - Calls handlers for each event type
  - **Verification:** Unit test in `apps/web/src/lib/__tests__/sse.test.ts`

- [x] **P2.7: Extend API client for streaming**
  - Update `apps/web/src/lib/api.ts`
  - Add `streamGenerateCV(body, handlers)`:
    - POST to `/api/generate/stream`
    - Uses `parseSSE()` to handle events
    - Handlers: onRunStarted, onStepStarted, onStepCompleted, onReviewMemo, onResult, onError, onCompleted
  - **Verification:** Type-check passes

- [x] **P2.8: Extend Zustand store for streaming state**
  - Update `apps/web/src/lib/store.ts`
  - Add fields:
    - `generationTransport: "blocking" | "streaming"`
    - `activeThreadId: string | null`
    - `runStatus: "idle" | "running" | "completed" | "failed"`
    - `activeStep: string | null`
    - `completedSteps: string[]`
    - `liveReviewMemos: ReviewMemo[]`
    - `generationError: string | null`
  - Add setters for each field
  - **Verification:** Type-check passes

- [x] **P2.9: Create generation progress component**
  - Create `apps/web/src/components/generation-progress.tsx`
  - Display:
    - Current step with spinner
    - Completed steps with checkmarks
    - Live reviewer memos as they arrive
    - Error state if generation fails
  - Use Zustand store for data
  - **Verification:** Unit test in `apps/web/src/components/__tests__/generation-progress.test.tsx`

- [x] **P2.10: Integrate streaming into upload step**
  - Update `apps/web/src/components/upload-step.tsx`
  - Keep existing "Quick Generate" button (calls blocking `generateCV()`)
  - Add new "Generate with Live Progress" button (calls `streamGenerateCV()`)
  - Show `<GenerationProgress />` when streaming is active
  - **Verification:** Manual smoke test both buttons work

- [x] **P2.11: Run full test suite**
  - Backend: `poetry run pytest backend/tests/api/test_generate_stream_api.py backend/tests/graph/test_stream_events.py`
  - Frontend: `cd apps/web && pnpm test -- --run`
  - Lint: `pnpm --filter @career-flow/web lint`
  - Build: `pnpm --filter @career-flow/web build`
  - **Verification:** All checks pass

### Atomic Commits (Phase 2)
1. `test(web): add vitest and testing-library harness`
2. `feat(backend): emit generation progress events and add streaming endpoint`
3. `feat(web): add POST SSE client and live progress state`
4. `feat(web): show live pipeline progress in upload flow`

### Acceptance Criteria (Phase 2)
- [ ] `curl -N -X POST http://localhost:8000/api/generate/stream` returns SSE events in correct order
- [ ] Frontend displays real-time progress for streaming mode
- [ ] Quick Generate (blocking mode) still works identically to Phase 1
- [ ] All tests pass

---

## Phase 3: Chat-First Frontend + Pre/Post Generation Chat

**Goal:** Make Assistant mode the primary UX (ChatGPT-style with artifacts). Quick Generate preserved.

### Implementation Tasks

- [x] **P3.1: Create chat schemas**
  - Create `backend/app/schemas/chat.py`
  - Define:
    - `ChatMessage` (id, role, content, kind, timestamp)
    - `IntakeTurnResult` (assistant_reply, ready_to_generate, extracted_constraints, missing_fields)
    - `RefinementResult` (assistant_reply, updated_cv_dict)
    - `ArtifactUpdate` (type, cv_data)
  - **Verification:** Import schemas, inspect types

- [x] **P3.2: Create intake agent**
  - Create `backend/app/agents/chat_prompts.py` with system prompts for intake and refinement
  - Create `backend/app/agents/intake.py`
  - Implement `intake_agent` (pydantic-ai Agent):
    - Takes conversation history, resume_text, job_description, user_instructions
    - Asks ONE clarifying question per turn (page count preference, emphasis areas, exclusions)
    - Returns `ready_to_generate: bool` when sufficient context gathered
    - Returns `extracted_constraints` and `missing_fields`
  - **Verification:** Unit test with mock conversation

- [x] **P3.3: Create refinement agent**
  - Create `backend/app/agents/refinement.py`
  - Implement `refinement_agent` (pydantic-ai Agent):
    - Takes current CV dict, resume_text, job_description, latest user message
    - Returns updated CV dict + assistant explanation
  - **Verification:** Unit test with sample CV and refinement request

- [x] **P3.4: Create chat LangGraph states**
  - Create `backend/app/graph/chat_state.py`
  - Define `IntakeState` TypedDict:
    ```python
    class IntakeState(TypedDict, total=False):
        messages: Annotated[list[ChatMessage], operator.add]
        resume_text: str
        job_description: str
        user_instructions: str | None
        extracted_constraints: list[str]
        missing_fields: list[str]
        ready_to_generate: bool
        assistant_reply: str | None
    ```
  - Define `RefinementState` TypedDict:
    ```python
    class RefinementState(TypedDict, total=False):
        messages: Annotated[list[ChatMessage], operator.add]
        current_cv_dict: dict[str, Any]
        resume_text: str
        job_description: str
        latest_user_message: str
        updated_cv_dict: dict[str, Any] | None
        assistant_reply: str | None
    ```
  - **Verification:** Import states, inspect types

- [x] **P3.5: Create chat graph nodes**
  - Create `backend/app/graph/nodes_chat.py`
  - Implement:
    - `intake_node(state: IntakeState, config) -> dict`
    - `refinement_node(state: RefinementState, config) -> dict`
  - **Verification:** Import nodes, inspect signatures

- [x] **P3.6: Build chat graphs**
  - Create `backend/app/graph/build_chat_graphs.py`
  - Implement `build_intake_graph() -> StateGraph`
  - Implement `build_refinement_graph() -> StateGraph`
  - Update `backend/app/graph/registry.py` to compile and cache them
  - **Verification:** Draw mermaid diagrams for both graphs

- [ ] **P3.7: Create chat API endpoints**
  - Create `backend/app/api/chat.py`
  - Add routes:
    - `POST /api/chat/intake/stream` (SSE)
    - `POST /api/chat/generate/stream` (SSE, reuses generation graph)
    - `POST /api/chat/refine/stream` (SSE)
  - Register in `backend/app/main.py`
  - Define request/response models
  - SSE events:
    - `chat.message.delta` (token streaming)
    - `chat.message.completed`
    - `intake.ready` (ready_to_generate flag + constraints)
    - `artifact.cv.updated` (CV data changed)
  - **Verification:** `lsp_diagnostics` clean, routes registered

- [ ] **P3.8: Write backend chat tests**
  - Create `backend/tests/graph/test_intake_graph.py`
  - Test intake asks questions until ready
  - Create `backend/tests/graph/test_refinement_graph.py`
  - Test refinement updates CV correctly
  - Create `backend/tests/api/test_chat_api.py`
  - Test all 3 streaming endpoints
  - **Verification:** `poetry run pytest backend/tests/graph/test_intake_graph.py backend/tests/graph/test_refinement_graph.py backend/tests/api/test_chat_api.py`

- [ ] **P3.9: Extend Zustand store for chat state**
  - Update `apps/web/src/lib/store.ts`
  - Add fields (flat, no slices):
    - `uiMode: "assistant" | "quick"`
    - `chatMessages: ChatMessage[]`
    - `chatPhase: "intake" | "generation" | "refinement"`
    - `chatInput: string`
    - `artifactTab: "cv" | "preview" | "reviews"`
    - `assistantStatus: "idle" | "thinking" | "streaming" | "awaiting_input"`
    - `intakeReady: boolean`
  - Add setters and array manipulation helpers
  - **Verification:** Type-check passes

- [ ] **P3.10: Extend API client for chat endpoints**
  - Update `apps/web/src/lib/api.ts`
  - Add:
    - `streamIntakeChat(messages, handlers)`
    - `streamAssistantGenerate(messages, resume, jd, handlers)`
    - `streamRefinementChat(threadId, messages, cvData, handlers)`
  - **Verification:** Type-check passes

- [ ] **P3.11: Create chat workspace component**
  - Create `apps/web/src/components/chat-workspace.tsx`
  - Implements Assistant mode orchestration:
    - Phase: intake → generation → refinement
    - Manages chat message list and composer
    - Calls appropriate streaming endpoint per phase
  - **Verification:** Unit test in `apps/web/src/components/__tests__/chat-workspace.test.tsx`

- [ ] **P3.12: Create chat UI components**
  - Create `apps/web/src/components/chat-message-list.tsx` (renders message history)
  - Create `apps/web/src/components/chat-composer.tsx` (input + send button)
  - Create `apps/web/src/components/artifact-panel.tsx` (tabs: CV editor, preview, reviews)
  - **Verification:** Individual unit tests for each

- [ ] **P3.13: Refactor page.tsx for two-pane layout**
  - Update `apps/web/src/app/page.tsx`
  - Replace step-based rendering with mode toggle
  - Layout:
    - Mode toggle at top: `[Assistant] [Quick Generate]`
    - If `uiMode === "assistant"`:
      - Left pane (50%): `<ChatWorkspace />`
      - Right pane (50%): `<ArtifactPanel />`
    - If `uiMode === "quick"`:
      - Full width: `<UploadStep />` (unchanged)
  - **Verification:** Manual smoke test both modes

- [ ] **P3.14: Update artifact panel to reuse existing components**
  - Update `apps/web/src/components/artifact-panel.tsx`
  - Tabs:
    - "CV": Embed `<CVEditor />` (from existing cv-editor.tsx)
    - "Preview": Embed `<PreviewPanel />` (from existing preview-panel.tsx, make sticky behavior optional)
    - "Reviews": Placeholder for Phase 4
  - **Verification:** CV editor and preview work inside artifact panel

- [ ] **P3.15: Update global styles for chat layout**
  - Update `apps/web/src/app/globals.css`
  - Add layout styles:
    - Two-pane flex container
    - Chat pane: sticky header, scrollable messages, fixed composer
    - Artifact pane: tabs + content
    - Mobile: collapse to single pane with toggle
  - **Verification:** Responsive behavior works on desktop and mobile viewport

- [ ] **P3.16: Run full test suite**
  - Backend: `poetry run pytest backend/tests/graph/test_intake_graph.py backend/tests/graph/test_refinement_graph.py backend/tests/api/test_chat_api.py`
  - Frontend: `pnpm --filter @career-flow/web test -- --run`
  - Lint: `pnpm --filter @career-flow/web lint`
  - Build: `pnpm --filter @career-flow/web build`
  - **Verification:** All checks pass

- [ ] **P3.17: Manual smoke test**
  - Start app in Assistant mode
  - Upload resume + paste JD
  - Verify intake asks clarifying questions
  - Verify generation runs and CV appears in artifact panel
  - Verify refinement works (user requests change, CV updates)
  - Switch to Quick Generate mode
  - Verify old flow still works unchanged
  - **Verification:** Both modes fully functional

### Atomic Commits (Phase 3)
1. `feat(backend): add chat schemas and intake/refinement agents`
2. `feat(backend): add streaming chat endpoints and langgraph chat flows`
3. `feat(web): add assistant chat workspace and artifact panel`
4. `feat(web): keep quick generate as alternate mode in the same page`
5. `test(web): cover assistant mode and quick mode regression flows`

### Acceptance Criteria (Phase 3)
- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Assistant mode: intake → generate → refine flow works end-to-end
- [ ] Quick Generate mode unchanged and functional
- [ ] Build succeeds with zero errors

---

## Phase 4: HITL Interrupts + Interactive Review Committee

**Goal:** Pause generation after reviews, let users accept/reject recommendations, then resume.

### Implementation Tasks

- [ ] **P4.1: Extend review schemas for interaction**
  - Update `backend/app/schemas/review.py`
  - Add:
    - `InteractiveReviewItem` (item_key, recommendation, rationale, severity)
    - `InteractiveReviewMemo` (reviewer_role, items, overall_score, overall_rationale)
    - `ReviewDecision` (item_key, accepted: bool)
    - `ReviewApprovalPayload` (interactive_reviews, hallucination_report, consensus_score)
  - **Verification:** Import schemas, inspect types

- [ ] **P4.2: Create review normalization helper**
  - Create `backend/app/graph/review_normalization.py`
  - Implement `normalize_review_memo(memo: ReviewMemo, reviewer_role: str) -> InteractiveReviewMemo`:
    - Assigns deterministic `item_key` to each recommendation (e.g., `hr:0`, `hr:1`, `technical:0`)
    - Converts raw ReviewMemo to InteractiveReviewMemo
  - **Verification:** Unit test with sample ReviewMemo

- [ ] **P4.3: Add review_gate node to generation graph**
  - Update `backend/app/graph/build_generation_graph.py`
  - Add `review_gate` node after parallel reviewer nodes:
    - Normalizes all ReviewMemo results
    - Emits SSE event: `interrupt.pending` with `ReviewApprovalPayload`
    - Calls `interrupt(value=payload)` to pause graph
  - Add conditional edge: if `review_decisions` provided, continue to synthesis/validate
  - Update state schema in `backend/app/graph/state.py`:
    ```python
    interactive_reviews: list[InteractiveReviewMemo]
    awaiting_review_approval: bool
    review_decisions: dict[str, bool] | None
    ```
  - **Verification:** `lsp_diagnostics` clean

- [ ] **P4.4: Add review apply node**
  - Create `review_apply_node` in `backend/app/graph/nodes_generation.py`:
    - Takes `review_decisions` from state
    - Filters ReviewMemo list based on accepted items
    - If all rejected → skip synthesis, validate original draft
    - If some accepted → pass filtered memos to synthesis
  - Wire into graph after `review_gate`
  - **Verification:** Unit test with various decision combinations

- [ ] **P4.5: Create review resume endpoint**
  - Update `backend/app/api/chat.py`
  - Add `POST /api/chat/review/resume/stream`:
    - Request: `{thread_id, decisions: [{item_key, accepted}], api_key, model_name}`
    - Calls `graph.astream(Command(resume={"review_decisions": decisions}), config={"configurable": {"thread_id": ...}})`
    - Returns SSE stream continuing from interrupt
  - SSE events:
    - `review.resume.accepted` (accepted_count, rejected_count)
    - Then normal `step.started`, `artifact.cv.updated`, `result`, `run.completed`
  - **Verification:** `lsp_diagnostics` clean

- [ ] **P4.6: Write backend interrupt tests**
  - Create `backend/tests/graph/test_review_interrupts.py`
  - Test cases:
    - Interrupt emitted when reviews exist
    - Synthesis receives only accepted recommendations
    - All rejected → skip synthesis, validate original
    - Resume continues correctly
  - Create `backend/tests/api/test_review_resume_api.py`
  - Test resume endpoint
  - **Verification:** `poetry run pytest backend/tests/graph/test_review_interrupts.py backend/tests/api/test_review_resume_api.py`

- [ ] **P4.7: Update SSE events to include item_key**
  - Update `backend/app/graph/events.py`
  - `emit_review_memo()` now includes normalized `item_key` values
  - **Verification:** `lsp_diagnostics` clean

- [ ] **P4.8: Extend Zustand store for review approval state**
  - Update `apps/web/src/lib/store.ts`
  - Add fields:
    - `pendingReviewApproval: ReviewApprovalPayload | null`
    - `reviewDecisions: Record<string, boolean>` (item_key → accepted)
    - `isAwaitingReviewApproval: boolean`
  - Add setters
  - **Verification:** Type-check passes

- [ ] **P4.9: Create review committee panel component**
  - Create `apps/web/src/components/review-committee-panel.tsx`
  - Displays all interactive review memos
  - For each reviewer (HR, Technical, ATS):
    - Show overall score and rationale
    - List all recommendations with accept/reject toggles
  - Submit button calls resume endpoint
  - **Verification:** Unit test in `apps/web/src/components/__tests__/review-committee-panel.test.tsx`

- [ ] **P4.10: Create reviewer memo card component**
  - Create `apps/web/src/components/reviewer-memo-card.tsx`
  - Shows single reviewer's findings
  - Individual item toggles for accept/reject
  - Visual severity indicators
  - **Verification:** Unit test

- [ ] **P4.11: Integrate review panel into artifact panel**
  - Update `apps/web/src/components/artifact-panel.tsx`
  - Add "Reviews" tab (previously placeholder)
  - Show `<ReviewCommitteePanel />` when `pendingReviewApproval` is set
  - **Verification:** Manual smoke test

- [ ] **P4.12: Update chat-workspace for interrupt handling**
  - Update `apps/web/src/components/chat-workspace.tsx`
  - When `interrupt.pending` event received:
    - Set `isAwaitingReviewApproval = true`
    - Store payload in `pendingReviewApproval`
    - Pause composer submission
    - Switch artifact tab to "Reviews"
  - When user approves/rejects and submits:
    - Call `streamReviewResume(thread_id, decisions)`
    - Continue stream with same handlers
  - **Verification:** Manual smoke test interrupt flow

- [ ] **P4.13: Verify Quick Generate unaffected**
  - Test that Quick Generate (blocking endpoint) still runs review mode without interrupts
  - Synthesis runs automatically
  - **Verification:** Manual smoke test Quick Generate with review_mode=true

- [ ] **P4.14: Run full test suite**
  - Backend: `poetry run pytest backend/tests/graph/test_review_interrupts.py backend/tests/api/test_review_resume_api.py`
  - Frontend: `pnpm --filter @career-flow/web test -- --run`
  - Lint: `pnpm --filter @career-flow/web lint`
  - Build: `pnpm --filter @career-flow/web build`
  - **Verification:** All checks pass

- [ ] **P4.15: Manual end-to-end test**
  - Assistant mode, review enabled
  - Verify interrupt happens after reviews complete
  - Verify UI shows all reviewer memos
  - Accept some, reject others
  - Verify synthesis uses only accepted recommendations
  - Verify final CV reflects decisions
  - **Verification:** Full HITL flow works

### Atomic Commits (Phase 4)
1. `feat(backend): add interactive review schemas and normalization helpers`
2. `feat(backend): add langgraph review interrupt gate and resume endpoint`
3. `feat(web): render live reviewer memos and approval UI`
4. `test: cover interrupt, resume, and quick-generate regression cases`

### Acceptance Criteria (Phase 4)
- [ ] All tests pass
- [ ] Assistant mode pauses at review gate
- [ ] Users can accept/reject individual recommendations
- [ ] Synthesis respects user decisions
- [ ] Quick Generate unaffected (auto-synthesis, no interrupt)

**⚠️ Note:** Until Phase 5, interrupts are in-memory only. Process restart loses interrupt state. Ship Phase 5 immediately after.

---

## Phase 5: Session Persistence + History

**Goal:** SQLite checkpointing for durable sessions. History browsing. Resume after restart.

### Implementation Tasks

- [ ] **P5.1: Add SQLite checkpointer dependency**
  - Update `backend/pyproject.toml`: add `langgraph-checkpoint-sqlite`
  - Run `poetry install`
  - **Verification:** `poetry show langgraph-checkpoint-sqlite`

- [ ] **P5.2: Add session settings**
  - Update `backend/app/config.py`
  - Add settings:
    - `langgraph_sqlite_path: str = "data/langgraph.db"`
    - `session_page_size_default: int = 20`
  - Create `data/` directory in .gitignore
  - **Verification:** `lsp_diagnostics` clean

- [ ] **P5.3: Create session metadata store**
  - Create `backend/app/services/session_store.py`
  - Implement `SessionStore` class using stdlib `sqlite3`:
    - Initialize tables:
      - `session_runs` (thread_id, title, mode, status, created_at, updated_at, model_name, review_model, requires_api_key_on_resume, latest_assistant_message, has_cv)
      - `session_messages` (thread_id, message_id, role, content, kind, timestamp)
    - Methods:
      - `create_session(thread_id, ...)`
      - `update_session(thread_id, ...)`
      - `list_sessions(limit, cursor) -> (sessions, next_cursor)`
      - `get_session(thread_id) -> session_detail`
      - `add_message(thread_id, message)`
  - **Verification:** Unit test in `backend/tests/services/test_session_store.py`

- [ ] **P5.4: Create session schemas**
  - Create `backend/app/schemas/session.py`
  - Define:
    - `SessionSummary` (thread_id, title, mode, status, created_at, updated_at, latest_assistant_message, has_cv, requires_api_key_on_resume)
    - `SessionDetail` (extends SessionSummary + messages, cv_data, review_panel, pending_interrupt)
    - `SessionListResponse` (items, next_cursor)
  - **Verification:** Import schemas, inspect types

- [ ] **P5.5: Initialize SQLite checkpointer in app lifespan**
  - Update `backend/app/main.py`
  - In lifespan:
    - Initialize `AsyncSqliteSaver` from settings.langgraph_sqlite_path
    - Call `await checkpointer.setup()` to create tables
    - Initialize `SessionStore` from same SQLite path
    - Attach both to `app.state.checkpointer` and `app.state.session_store`
  - **Verification:** App starts, SQLite file created

- [ ] **P5.6: Update graph registry to use persistent checkpointer**
  - Update `backend/app/graph/registry.py`
  - `get_generation_graph(checkpointer)` now requires checkpointer arg
  - All API endpoints pass `app.state.checkpointer`
  - **Verification:** `lsp_diagnostics` clean

- [ ] **P5.7: Update API endpoints to write session metadata**
  - Update `backend/app/api/chat.py` and `backend/app/api/generate.py`:
    - Before invoking graph: `session_store.create_session(thread_id, ...)`
    - After stream completes: `session_store.update_session(thread_id, status="completed")`
    - On error: `session_store.update_session(thread_id, status="failed")`
    - On interrupt: `session_store.update_session(thread_id, status="interrupted")`
    - Store every chat message: `session_store.add_message(thread_id, message)`
  - Never store API keys in session metadata — only `requires_api_key_on_resume` flag
  - **Verification:** `lsp_diagnostics` clean

- [ ] **P5.8: Create session API endpoints**
  - Create `backend/app/api/sessions.py`
  - Add routes:
    - `GET /api/sessions?limit=20&cursor=...` (paginated list)
    - `GET /api/sessions/{thread_id}` (detail)
  - Register in `backend/app/main.py`
  - **Verification:** `lsp_diagnostics` clean, routes registered

- [ ] **P5.9: Write session persistence tests**
  - Update `backend/tests/services/test_session_store.py`
  - Test CRUD operations
  - Create `backend/tests/api/test_sessions_api.py`
  - Test list and detail endpoints
  - Create `backend/tests/integration/test_sqlite_resume_across_restart.py`
  - Test:
    - Start graph, interrupt, stop server, restart server, resume
    - Verify state fully restored
  - **Verification:** `poetry run pytest backend/tests/services/ backend/tests/api/test_sessions_api.py backend/tests/integration/test_sqlite_resume_across_restart.py`

- [ ] **P5.10: Extend Zustand store for session history**
  - Update `apps/web/src/lib/store.ts`
  - Add fields:
    - `sessionSummaries: SessionSummary[]`
    - `activeSessionId: string | null`
    - `activeSessionStatus: string | null`
    - `requiresApiKeyOnResume: boolean`
  - Add setters
  - **Verification:** Type-check passes

- [ ] **P5.11: Extend API client for session endpoints**
  - Update `apps/web/src/lib/api.ts`
  - Add:
    - `listSessions(limit, cursor): Promise<SessionListResponse>`
    - `getSession(threadId): Promise<SessionDetail>`
  - **Verification:** Type-check passes

- [ ] **P5.12: Create session history sidebar component**
  - Create `apps/web/src/components/session-history-sidebar.tsx`
  - Features:
    - List recent sessions
    - Show status icons (running, interrupted, completed, failed)
    - Click to load session
    - "New Session" button
    - Pagination (load more)
  - Desktop: fixed left rail
  - Mobile: dialog-based drawer
  - **Verification:** Unit test in `apps/web/src/components/__tests__/session-history-sidebar.test.tsx`

- [ ] **P5.13: Implement session hydration in chat-workspace**
  - Update `apps/web/src/components/chat-workspace.tsx`
  - On session load:
    - Fetch `GET /api/sessions/{thread_id}`
    - Restore `chatMessages` from session detail
    - Restore `cvData` if exists
    - Restore `pendingReviewApproval` if session is interrupted
    - Restore `chatPhase` based on session state
    - Switch to correct artifact tab
    - If `requires_api_key_on_resume`, prompt user for API key before resume
  - **Verification:** Manual smoke test load past session

- [ ] **P5.14: Integrate session sidebar into page.tsx**
  - Update `apps/web/src/app/page.tsx`
  - Add `<SessionHistorySidebar />` in Assistant mode
  - Layout: sidebar (20%) | chat pane (40%) | artifact pane (40%)
  - Mobile: sidebar as overlay drawer
  - **Verification:** Manual smoke test history browsing

- [ ] **P5.15: Run full test suite**
  - Backend: `poetry run pytest backend/tests/services/test_session_store.py backend/tests/api/test_sessions_api.py backend/tests/integration/test_sqlite_resume_across_restart.py`
  - Frontend: `pnpm --filter @career-flow/web test -- --run`
  - Lint: `pnpm --filter @career-flow/web lint`
  - Build: `pnpm --filter @career-flow/web build`
  - **Verification:** All checks pass

- [ ] **P5.16: Manual end-to-end test**
  - Create session in Assistant mode
  - Interrupt at review gate
  - Stop server
  - Restart server
  - Load session from history
  - Verify full state restored (messages, CV, pending interrupt)
  - Resume session, complete generation
  - Verify session appears as "completed" in history
  - **Verification:** Full persistence flow works

### Atomic Commits (Phase 5)
1. `feat(backend): add sqlite checkpointing and session metadata store`
2. `feat(backend): add session list/detail APIs and restart-safe resume`
3. `feat(web): add session history sidebar and session hydration flow`
4. `test: cover sqlite persistence, list/detail APIs, and resume after restart`

### Acceptance Criteria (Phase 5)
- [ ] All tests pass
- [ ] Sessions survive process restarts
- [ ] Session history shows all past generations
- [ ] Session detail loads with full state (messages, CV, interrupt state)
- [ ] Resume works correctly, prompting for API key if needed
- [ ] Build succeeds

---

## Final Verification Wave

After all 5 phases complete, run comprehensive verification:

- [ ] **F1: Full backend test suite**
  - `cd backend && poetry run pytest tests/`
  - All tests pass (unit, integration, API)
  - **Verification:** Zero failures

- [ ] **F2: Full frontend test suite**
  - `cd apps/web && pnpm test -- --run`
  - All tests pass
  - **Verification:** Zero failures

- [ ] **F3: Type checking**
  - `pnpm type-check` (monorepo root)
  - Zero TypeScript errors
  - **Verification:** Clean output

- [ ] **F4: Build production bundle**
  - `pnpm build`
  - Both frontend and backend build successfully
  - **Verification:** Exit code 0

- [ ] **F5: End-to-end smoke test (Assistant mode)**
  - Start fresh session
  - Upload resume + JD
  - Complete intake conversation (3-5 turns)
  - Generate CV with review mode
  - Review committee interrupt
  - Accept/reject recommendations
  - Synthesis completes
  - Refine CV (2-3 changes)
  - Download PDF
  - **Verification:** Full flow completes without errors

- [ ] **F6: End-to-end smoke test (Quick Generate mode)**
  - Switch to Quick Generate
  - Upload resume + JD
  - Click "Quick Generate"
  - CV generates (no interrupts)
  - Edit CV
  - Download PDF
  - **Verification:** Legacy flow unchanged and functional

- [ ] **F7: Session persistence verification**
  - Create interrupted session
  - Stop server
  - Restart server
  - Load session from history
  - Resume and complete
  - **Verification:** Session survives restart

- [ ] **F8: Multi-provider LLM verification**
  - Test with Google Gemini model
  - Test with OpenAI GPT-4 model
  - Test with Anthropic Claude model
  - **Verification:** All providers work correctly

- [ ] **F9: Anti-hallucination verification**
  - Generate CV with content NOT in resume
  - Verify hallucination warnings appear
  - Verify deterministic validator catches issues
  - **Verification:** Safety mechanisms active

- [ ] **F10: Mobile responsiveness**
  - Test on mobile viewport
  - Chat interface usable
  - Artifact panel collapses correctly
  - Session history accessible via drawer
  - **Verification:** Mobile UX functional

---

## Cross-Phase Rules

**Secrets Management:**
- API keys NEVER enter `GenerationState` or any checkpointed state
- Always use `GraphRuntimeConfig` for secrets (runtime-only)
- Session metadata stores `requires_api_key_on_resume` flag, not the key itself

**Testing:**
- Write tests BEFORE implementation where possible (TDD)
- Mock all LLM calls in tests (no real API usage)
- Each phase must pass its own test suite before moving to next phase

**Backward Compatibility:**
- Quick Generate flow MUST remain functional after every phase
- Blocking `/api/generate` endpoint preserved throughout
- Frontend can run both modes side-by-side

**Git Workflow:**
- Each phase works in its own git worktree branch
- Atomic commits per phase (self-contained, non-breaking)
- Merge to main only when phase is complete and all tests pass

**Architecture:**
- LangGraph in `backend/app/graph/` (separate from `agents/`)
- pydantic-ai agents stay pure (no LangGraph awareness)
- No LangChain dependency
- No PostgreSQL or Docker

---

## Risks & Mitigations

| Risk | Phase | Mitigation |
|---|---|---|
| Response schema drift breaks frontend | 1 | Regression tests against current GenerateResponse |
| LangGraph failures become all-or-nothing | 1 | Per-node exception catching, review_errors list |
| SSE stream failures after partial UI updates | 2 | Explicit terminal events (error, run.completed) |
| Unbounded chat loops | 3 | 1-question-per-turn limit, ready_to_generate flag |
| Artifact state drift from chat state | 3 | cvData as single source of truth in Zustand |
| Quick Generate accidentally broken | 3 | Prominent mode toggle, dedicated test suite |
| Interrupt state lost on restart (before Phase 5) | 4 | Document limitation, ship Phase 5 immediately after |
| Reviewer payload size too large | 4 | Normalized memos with stable keys, not raw events |
| SQLite write locks under concurrency | 5 | Single shared saver in lifespan, short writes |
| Checkpoint storage growth | 5 | Store document references, not full text; implement TTL |
| API key can't be restored safely | 5 | requires_api_key_on_resume flag, re-prompt on resume |

---

## Notes

- **LangGraph version:** 0.3+ (2025-2026)
- **Total estimated tasks:** ~90-100 implementation tasks across 5 phases
- **Effort per phase:** P1 (Short), P2 (Medium), P3 (Large), P4 (Medium), P5 (Medium)
- **Dependency chain:** Must be executed in order (1→2→3→4→5)
- **Phase 4 → Phase 5 urgency:** Ship immediately — interrupts are in-memory only until Phase 5
- **Testing philosophy:** TDD where possible, comprehensive coverage, mock all LLM calls
- **Architecture philosophy:** Hybrid approach (LangGraph orchestration + pydantic-ai leaf nodes) preserves project strengths while gaining advanced capabilities

---

**Plan Status:** Ready to Start  
**Last Updated:** 2026-03-16  
**Next Action:** Create git worktree and begin Phase 1

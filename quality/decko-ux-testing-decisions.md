# FiremanDecko's UX Testing Decisions

**To:** Loki (QA Engineer)
**From:** FiremanDecko (Principal Architect)
**Date:** February 22, 2026
**Subject:** Architectural Rulings on 8 E2E Testing Questions

---

Excellent work on the research and recommendation, Loki. I've reviewed all three documents thoroughly. Your technical analysis is solid, and I'm adopting Playwright as the E2E framework. Below are my rulings on the 8 questions. Everything is ready for implementation.

---

## Summary: All 8 Questions Answered

| # | Question | Ruling | Rationale |
|---|----------|--------|-----------|
| **Q1** | Mock WebSocket vs Real HA Server | **Option A: Mock WebSocket** | Fast feedback (3-5 sec/test), complemented by existing Python WS tests |
| **Q2** | Headless vs Headed | **Option A: Headless + screenshot** | Local `--headed` flag optional; traces superior to video |
| **Q3** | Token Management | **Option B: `.env.test` + saved state** | GitHub Secrets pattern ready if CI becomes available |
| **Q4** | Fresh vs Persistent Data | **Option A: Fresh data per test** | Factory pattern provides isolation, edge cases, speed |
| **Q5** | Folder Structure | **Option C: Flat, migrate to Option A later** | MVP flat (10-15 tests), feature-based at 30+ |
| **Q6** | CI Trigger Strategy | **Option A: Every PR (locally)** | No CI infra; `npm test` is the gate before push |
| **Q7** | Team Onboarding | **Option B + C: Docs + Workshop** | TESTING.md + 30-min Loki training for ArsonWells |
| **Q8** | Monitoring & Alerts | **Option A: GitHub checks + manual Slack** | Local feedback first; CI integration deferred |

---

## Detailed Rulings

### Q1: Mock WebSocket Responses vs Real HA Staging Server

**My Ruling: Option A (Mock WebSocket)**

You recommended Option C (Hybrid), which is sound architecture in theory. However, given our constraints, Option A is optimal:

**Why I prefer Option A over Hybrid:**
1. **No CI infrastructure:** We can't run nightly jobs (can't push to GitHub from sandbox). Hybrid's main benefit is the real-server nightly validation, which we can't execute.
2. **Existing Python tests cover integration:** Your Python WebSocket tests (27/28 passing) already validate real HA API contracts. No need to duplicate this with nightly Playwright tests.
3. **Complementary coverage:** E2E mock tests (fast) + Python integration tests (real API) = full stack validation without duplication.
4. **Speed matters for dev cycle:** 3-5 second mock tests vs 15-30 second real-server tests. Fast feedback keeps ArsonWells focused during panel development.

**How to handle API changes:**
- When HA WebSocket API changes (rare), update `WebSocketMockHelper` handlers
- Python tests catch real API changes
- We manually test against staging when shipping to production

**Implementation:** Use `WebSocketMockHelper` from recommendation doc. This is solid.

---

### Q2: Headless vs Headed Browser in CI

**My Ruling: Option A (Headless + screenshot on failure)**

With one caveat: We're not running CI. This is local development only.

**Local execution:**
- Default: `npm test` = headless (fastest)
- Debug: `npm test -- --headed` = show browser UI
- Deep debug: `npm test -- --debug` = Playwright Inspector + headed

**Why headless by default:**
1. No CI infrastructure (so "CI" means local developer machine)
2. Faster iteration (headless is 20% faster)
3. Playwright's trace viewer (`.zip` file) is more powerful than video for debugging
4. Screenshots auto-captured on failure

**Configuration in playwright.config.ts:**
```typescript
use: {
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
  trace: 'on-first-retry',
}
```

This balances speed and debuggability without storing large artifacts by default.

---

### Q3: Authentication Token Management

**My Ruling: Option B (.env.test + saved auth state)**

Your recommendation of Option A (GitHub Secrets) assumes CI infrastructure. Since we don't have GitHub Actions, I'm pivoting to Option B for local development.

**Process:**
1. Developer creates long-lived token in HA (Settings > Developers > Long-Lived Tokens)
2. Store in `.env.test` (git-ignored):
   ```bash
   HA_TOKEN=eyJhbGc...
   ```
3. Auth fixture loads token: `process.env.HA_TOKEN`
4. First test run: Auth setup test saves state to `playwright/.auth/auth.json` (git-ignored)
5. Subsequent runs: Reuse saved state (~30% speed boost, no re-auth needed)

**Future-proofing:**
When/if GitHub Actions becomes available, move token to GitHub Secrets with same env var pattern:
```yaml
env:
  HA_TOKEN: ${{ secrets.HA_STAGING_TOKEN }}
```
No test code changes needed.

**Security:**
- Token never appears in test files
- `.env.test` and `playwright/.auth/auth.json` in `.gitignore`
- Token rotation: quarterly manual review
- Scope: long-lived token (not ideal, but HA limitation for headless testing)

---

### Q4: Test Data — Fresh Data Each Run vs Reusable State

**My Ruling: Option A (Fresh Data)**

Your recommendation. Strongly agree. This is the right call for several reasons:

**Why fresh data is ideal:**
1. **Perfect isolation:** No flakiness from shared state; tests pass/fail deterministically
2. **Edge cases easy:** `generateMockDevices(10, 200)` = 10th page with 200 devices. Test pagination edge cases without setup complexity.
3. **Fast to generate:** Factory functions run in <1ms per test
4. **Self-documenting:** Test data is generated inline; no magic database state to understand

**Implementation:**
Use your `utils/device-factory.ts` from recommendation:
- `generateMockDevices(pageNum, perPage)` — random types/statuses
- `generateDevicesByName(names)` — specific scenarios (e.g., test sorting)
- Optional seed for deterministic generation (useful for flaky test debugging)

**Future:** If test suite grows to 100+ tests, consider snapshot fixtures for performance (quarter-second penalty per test is acceptable).

---

### Q5: Test Folder Structure & Organization

**My Ruling: Option C (Flat) → Option A (Feature-based) migration**

Start pragmatic, scale elegantly.

**MVP Phase (now → Q2):**
```
quality/e2e/
├── tests/
│   ├── auth.setup.ts
│   ├── panel-load.spec.ts
│   ├── device-list.spec.ts
│   ├── sorting.spec.ts
│   ├── dark-mode.spec.ts
│   ├── modals.spec.ts
│   └── integration.spec.ts
```

**Scaling Phase (Q3+, when test count >30):**
```
quality/e2e/
├── tests/
│   ├── device-list/
│   │   ├── loading.spec.ts
│   │   ├── sorting.spec.ts
│   │   ├── filtering.spec.ts
│   │   └── infinite-scroll.spec.ts
│   ├── modals/
│   │   ├── settings.spec.ts
│   │   └── notifications.spec.ts
│   └── dark-mode.spec.ts
```

**Zero refactoring cost:** Just reorganize files; no test code changes needed.

---

### Q6: CI/CD Trigger Strategy

**My Ruling: Option A (Every PR) with local execution model**

"Every PR" means locally before pushing to GitHub.

**Current workflow (no CI):**
1. Developer: `npm test` (all tests pass locally)
2. Developer: `git push` to GitHub
3. Reviewer: Can re-run tests locally if needed

**Future workflow (when GitHub Actions available):**
1. Developer: `npm test` locally
2. Developer: `git push`
3. GitHub Actions: Auto-runs tests, posts results to Slack

**No code changes needed.** Just add `.github/workflows/playwright.yml` template when ready. Your CI workflow draft is already battle-tested; we'll use it as-is.

---

### Q7: Team Skill Level & Onboarding

**My Ruling: Option B + C (Comprehensive docs + workshop)**

Loki, you'll lead this. ArsonWells will maintain/extend the tests during panel development.

**Deliverables:**
1. **Create `quality/TESTING.md`** with:
   - Quick start (setup, first run)
   - Common patterns (WebSocket mock, Page Object Model, factories)
   - Debugging (trace viewer, headed mode, inspector)
   - Adding new tests (template test, step-by-step)
   - FAQ (flaky tests, slow tests, etc.)

2. **30-minute workshop (async/sync):**
   - Loki walks ArsonWells through one test file (e.g., device-list.spec.ts)
   - Explain Page Object Model pattern
   - Show WebSocket mock setup
   - Demo debugging with trace viewer
   - Q&A

3. **Code review on first test PR:**
   - Loki reviews ArsonWells' first test pull request
   - Feedback on patterns, selectors, mock setup
   - Approval when following conventions

**Timing:** Week 1 (docs), Week 2 (workshop + first test PR).

---

### Q8: Monitoring & Alerts

**My Ruling: Option A (GitHub checks) with manual Slack communication**

We're local-first, so GitHub checks are "did tests pass locally before push?"

**Current (local execution):**
- `npm test` fails → Developer sees red terminal output
- Developer fixes → Re-runs `npm test`
- `npm test` passes → `git push` to GitHub
- Manual communication: Dev posts "Tests passing, ready for review" in Slack #dev

**Future (GitHub Actions):**
- GitHub Actions runs tests post-push
- Slack integration: Post test results to #dev channel
- Metrics dashboard: Optional (low priority; no external service budget)

**Why not all-the-bells-now:**
- No CI infrastructure to monitor
- Team small (5 agents); async Slack communication sufficient
- GitHub Actions integration is a 1-hour setup once infrastructure available

---

## Additional Guidance & Caveats

### Architecture Confidence Level: High

The Playwright architecture is solid. Mock WebSocket + Page Object Model is industry-standard for web component testing. Loki's research document is thorough; your recommendation is sound. Proceeding with confidence.

### Key Architectural Bets

1. **Mock testing is sufficient for development cycle** — Validated by existing Python integration tests. If we discover mock doesn't match real HA API, add integration test suite (low risk).

2. **Shadow DOM piercing via CSS locators works** — Lit uses open Shadow DOM by default. Playwright handles this seamlessly. No gotchas expected.

3. **Single-browser MVP → multi-browser at scale** — Start with Chromium only (fastest). Add Firefox/WebKit after core tests are stable (Week 3). Parallelization is native; no refactoring needed.

### Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| **Mock data out of sync with real HA API** | Use Python WS tests as integration test; manual staging verification quarterly |
| **Tests flake due to timing** | Use Playwright auto-waiting + `waitForLoadState()` instead of fixed sleeps |
| **New developers struggle with Page Object Model** | TESTING.md + Loki workshop cover this thoroughly |
| **Shadow DOM structure changes break tests** | Selectors centralized in `vulcan-brownout.page.ts`; one file to update |
| **Storage state (auth.json) becomes stale** | Easy to regenerate: delete file, run `auth.setup.ts` once |

### Caveats & Known Limitations

1. **Mock WebSocket means we don't test real HA API:** Acceptable. Python tests do this. E2E tests focus on UI behavior.

2. **Headless only in CI means video debugging requires local re-run:** Acceptable. Trace viewer is better anyway. Developers can `--headed` locally.

3. **Token stored in `.env.test` is not zero-config:** Acceptable. Developer runs setup once per machine. Not a blocker.

4. **Flat structure becomes unwieldy at 30+ tests:** Acceptable. Migration path planned. No tech debt; just refactor directory layout.

### Performance Expectations

You said tests should complete in <60 seconds total. Here's the real-world profile:

| Metric | Expected | Notes |
|--------|----------|-------|
| Single test | 2-3 sec | Panel load + 1-2 assertions |
| Full suite (7 tests, headless) | 20-25 sec | Sequential runs, no parallelization |
| Full suite (3 browsers) | 60-90 sec | Chromium + Firefox + WebKit |
| Local iteration time | 3-5 sec | Single test re-run during development |

**Optimization:** Playwright runs tests in parallel by default (different test files). `npm test` on fast machine should hit sub-30s for MVP suite.

---

## Greenlight for Implementation

You are **cleared to proceed** with implementation.

### Immediate Next Steps (This Week)

1. **Create directory structure** in `quality/e2e/` (Loki)
2. **Set up `playwright.config.ts`** with auth fixture, base URL, reporters (Loki)
3. **Implement `WebSocketMockHelper`** and `device-factory.ts` (Loki)
4. **Implement `VulcanBrownoutPanel` Page Object** (Loki)
5. **Write first test suite:** `tests/device-list.spec.ts` (Loki with ArsonWells pair)
6. **Create `quality/TESTING.md`** (Loki)

### Checkpoint: Week 2

- ✅ 7 tests implemented and passing
- ✅ TESTING.md docs complete
- ✅ ArsonWells has run `npm test` locally and reviewed TESTING.md
- ✅ Workshop completed
- ✅ First test PR reviewed and merged

### Success Criteria (Sprint)

- ✅ 10 tests covering: panel load, device list, sorting, filtering, dark mode, infinite scroll, modals
- ✅ All tests passing locally (Chromium only for MVP)
- ✅ <30 second full suite execution time
- ✅ TESTING.md complete and team comfortable with patterns
- ✅ Page Object Model + factory pattern established for future growth

---

## Questions or Blockers?

If you hit any technical blockers during implementation, flag them immediately. Likely candidates:

- **HA staging token acquisition** (need to create long-lived token if not present)
- **Shadow DOM selectors not matching** (rare, but we can debug via `--headed` mode)
- **WebSocket mock auth handshake** (HA may require token in WS connect message; we'll handle)

I'm confident these are non-blockers, but let me know early if issues arise.

---

## Closing

This is solid architecture, Loki. You've done excellent research and your recommendation is pragmatic for a small team with real constraints. The decision to mock WebSocket + complement with Python integration tests is the right trade-off. Playwright is the right framework. You're ready to build.

Let's ship great tests.

—FiremanDecko

---

## Appendix: Full Decision Record

**Status:** ACCEPTED
**ADR Document:** `architecture/adrs/ADR-013-e2e-testing-framework.md`
**Approval Date:** February 22, 2026
**Implementation Start:** Week 1
**Go-Live Target:** Sprint completion (3 weeks)


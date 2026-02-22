# Architectural Questions for FiremanDecko - Vulcan Brownout E2E Testing

**From:** Loki (QA Engineer)
**Re:** Playwright E2E Testing Architecture Decisions
**Status:** Requires your input to finalize implementation

---

## Overview

This document outlines key architectural decisions that require your (FiremanDecko's) input before finalizing the Playwright E2E testing framework. I've completed the research and drafted a recommendation, but these questions have important tradeoffs that affect test design, CI/CD setup, and long-term maintainability.

---

## Critical Architectural Questions

### Q1: Mock WebSocket Responses vs Real HA Staging Server

**Context:**
The Vulcan Brownout panel communicates with HA via WebSocket (`this.hass.callWS()`). Tests need to validate this interaction.

**Options:**

**Option A: Mock WebSocket (Recommended in research)**
- Tests intercept WebSocket messages with `page.routeWebSocket()`
- Fully controlled test environment
- Fast execution (no network latency)
- Example:
  ```typescript
  await page.routeWebSocket('/api/websocket', (route) => {
    route.onMessage((msg) => {
      const data = JSON.parse(msg);
      if (data.type === 'get_devices') {
        route.send(JSON.stringify({ type: 'result', result: [...mocked devices] }));
      }
    });
  });
  ```

**Option B: Real HA Staging Server**
- Tests run against actual `homeassistant.lan:8123` instance
- Validates real API behavior
- Slower (network latency)
- Depends on staging server uptime
- Could catch API breaking changes early

**Option C: Hybrid Approach**
- Default: Mock WebSocket for unit E2E tests (fast, reliable)
- Nightly: Real server integration tests (validates API contract)
- Best of both worlds, but more complex CI setup

**Trade-offs:**

| Aspect | Option A (Mock) | Option B (Real) | Option C (Hybrid) |
|--------|---|---|---|
| **Speed** | ⭐⭐⭐⭐⭐ Fast | ⭐⭐ Slow | ⭐⭐⭐ Mixed |
| **Reliability** | ⭐⭐⭐⭐⭐ Always works | ⭐⭐⭐ Depends on server | ⭐⭐⭐⭐ Mostly reliable |
| **Catches API changes** | ❌ No | ✅ Yes | ✅ Yes (nightly) |
| **Cost (CI resources)** | $ Low | $$ Medium | $$$ High |
| **Maintenance** | Low | Low | Medium |
| **Team comfort** | Medium (new pattern) | High (traditional) | High |

**My Recommendation:** **Option C (Hybrid)**
- Fast feedback loop for development (mock-based)
- Real API validation via nightly/weekly runs
- Catches regressions without slowing PR testing

**Your Input Needed:**
- Are you comfortable with mock WebSocket testing for the core test suite?
- Should we set up a separate nightly job for real-server integration tests?
- Do you have existing HA staging environment we can use, or do we need to set up a test instance?

---

### Q2: Headless vs Headed Browser in CI

**Context:**
Tests can run in "headless" mode (no visible window) or "headed" mode (browser GUI visible via video recording).

**Options:**

**Option A: Headless in CI (Recommended)**
- Faster execution (no UI rendering overhead)
- Uses less CPU/memory
- Standard for CI/CD
- Videos only on failure (git can store them)
- Example: `npx playwright test --headless`

**Option B: Headed with Video Recording**
- Every test run recorded as video
- Better debugging (watch what happened)
- Slower, requires more disk space (~500MB per test run)
- Storage costs for artifacts

**Option C: Headless + Debug Mode on Failure**
- Default: Headless (fast)
- On failure: Re-run that test in headed mode with video
- More complex CI setup
- Best of both worlds if failure rate is low

**Trade-offs:**

| Aspect | Option A (Headless) | Option B (Always headed) | Option C (Failure debug) |
|--------|---|---|---|
| **Speed** | ⭐⭐⭐⭐⭐ Fastest | ⭐⭐ Slow | ⭐⭐⭐⭐ Good |
| **Debuggability** | ⭐⭐ Screenshots only | ⭐⭐⭐⭐⭐ Full video | ⭐⭐⭐⭐ When needed |
| **Storage cost** | $ Low | $$$ High | $$ Medium |
| **CI time** | 1-2 min | 3-5 min | 1-2 min (3-5 on failure) |

**My Recommendation:** **Option A (Headless) with screenshot on failure**
- Screenshots stored for all failures
- Trace viewer built-in (better than video for most debugging)
- Fastest, most cost-effective

**Your Input Needed:**
- Do you want video recordings of failures, or are screenshots + traces sufficient?
- Should we prioritize speed (headless) or debuggability?
- Any concerns about disk storage for artifacts in GitHub Actions?

---

### Q3: Authentication Token Management

**Context:**
HA uses long-lived tokens for authentication. Tests need this token to access the panel.

**Options:**

**Option A: GitHub Secrets (Recommended)**
```yaml
# .github/workflows/playwright.yml
- name: Run tests
  env:
    HA_TOKEN: ${{ secrets.HA_STAGING_TOKEN }}
  run: npm test
```

**Option B: Shared .env File**
```bash
# .env.test (git-ignored, shared on secure channel)
HA_TOKEN=eyJhbGc...
```

**Option C: Local Token Generation**
```typescript
// Tests generate token programmatically via HA API
const token = await generateTestToken('test-user', 'test-password');
```

**Trade-offs:**

| Aspect | Option A (Secrets) | Option B (.env) | Option C (Generate) |
|--------|---|---|---|
| **Security** | ⭐⭐⭐⭐⭐ Best | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Very good |
| **Setup ease** | ⭐⭐⭐⭐ Easy | ⭐⭐⭐⭐⭐ Easy | ⭐ Complex |
| **CI support** | ✅ Native | ⚠️ Manual | ✅ Native |
| **Rotation** | Easy (update secret) | Manual | Automatic |
| **Cost** | Free | Free | Requires test account |

**My Recommendation:** **Option A (GitHub Secrets)**
- Industry standard
- No hardcoded tokens
- Easy to rotate

**Your Input Needed:**
- Do you have a long-lived token we can use for staging tests?
- Should we create a dedicated "test user" account in staging HA?
- How often should we rotate the test token (monthly? quarterly)?
- Is there a process for managing GitHub Secrets in your workflow?

---

### Q4: Test Data: Fresh Data Each Run vs Reusable State

**Context:**
Tests need mock device data. Should each test run get a fresh list, or should state persist?

**Options:**

**Option A: Fresh Data Each Test (Recommended)**
```typescript
test.beforeEach(async ({ page }) => {
  // Generate new mock devices for each test
  const devices = generateMockDevices(0, 20);
  wsMock.registerDeviceListResponse([
    { page: 0, total: 60, devices }
  ]);
});
```

**Option B: Stateful/Persistent Data**
```typescript
// Database or file persists state across tests
// Tests can assume prior state (e.g., "Device 1 is now status 'on'")
```

**Option C: Hybrid (Snapshots)**
```typescript
// Create fixtures once, commit to git, reuse across runs
// Similar to playwright/.auth/auth.json approach
```

**Trade-offs:**

| Aspect | Option A (Fresh) | Option B (Persistent) | Option C (Snapshots) |
|--------|---|---|---|
| **Isolation** | ⭐⭐⭐⭐⭐ Perfect | ⭐ Coupled | ⭐⭐⭐⭐ Good |
| **Simplicity** | ⭐⭐⭐⭐⭐ Easy | ⭐⭐ Complex | ⭐⭐⭐ Moderate |
| **Flakiness** | ⭐⭐⭐⭐⭐ None | ⭐ High | ⭐⭐⭐ Low |
| **Debugging** | ⭐⭐ Generic data | ⭐⭐⭐⭐ Realistic state | ⭐⭐⭐⭐ Documented state |

**My Recommendation:** **Option A (Fresh Data)**
- Tests are independent
- No flakiness from shared state
- Easy to debug

**Your Input Needed:**
- Do you want tests to simulate realistic device scenarios (e.g., "Light is always on")?
- Should we create factory methods for specific test scenarios (e.g., `generateDevicesWithMixedStatus()`)?
- Any edge cases or specific device configurations that tests should validate?

---

### Q5: Test Folder Structure & Organization

**Context:**
How should tests be organized as the suite grows?

**Options:**

**Option A: Feature-based (Recommended)**
```
tests/
├── device-list/
│   ├── loading.spec.ts
│   ├── sorting.spec.ts
│   ├── filtering.spec.ts
│   └── infinite-scroll.spec.ts
├── modals/
│   ├── settings.spec.ts
│   └── notifications.spec.ts
└── dark-mode.spec.ts
```

**Option B: Layer-based**
```
tests/
├── unit/
│   ├── vulcan-brownout-panel.spec.ts
├── integration/
│   ├── websocket-api.spec.ts
└── e2e/
    └── user-flows.spec.ts
```

**Option C: Flat (Current recommendation)**
```
tests/
├── panel-load.spec.ts
├── device-list.spec.ts
├── sorting.spec.ts
├── dark-mode.spec.ts
├── modals.spec.ts
└── integration.spec.ts
```

**Trade-offs:**

| Aspect | Option A (Feature) | Option B (Layer) | Option C (Flat) |
|--------|---|---|---|
| **Scalability** | ⭐⭐⭐⭐⭐ Great | ⭐⭐⭐ OK | ⭐⭐ Gets crowded |
| **Discoverability** | ⭐⭐⭐⭐⭐ Clear | ⭐⭐⭐ OK | ⭐⭐⭐ OK |
| **Setup/Fixtures** | ⭐ Duplicated | ⭐⭐⭐⭐ Shared | ⭐⭐⭐⭐⭐ Shared easily |
| **Run subset** | ⭐⭐⭐⭐⭐ Easy | ⭐⭐⭐ OK | ⭐⭐⭐ OK |

**My Recommendation:** **Option A (Feature-based)** for large suite, **Option C (Flat)** for MVP

- Start flat, migrate to feature-based as suite grows
- Initially: ~10-15 test files
- After 6 months: Likely 50+ tests, warrant organization

**Your Input Needed:**
- How many test files do you anticipate in 6 months? (rough estimate)
- Should tests be organized by UI feature (device-list, settings modal, etc.) or by test type (unit, integration, E2E)?
- Any existing testing conventions in the Vulcan Brownout project I should follow?

---

### Q6: CI/CD Trigger Strategy

**Context:**
When should tests run automatically?

**Options:**

**Option A: Run on Every PR (Recommended for MVP)**
```yaml
on:
  pull_request:
    branches: [main, develop]
    paths:
      - 'frontend/**'
      - 'quality/e2e/**'
```

**Option B: Manual Trigger Only**
- Tests run only when developer explicitly triggers them
- Reduces CI load
- Risk: Tests not run before merge

**Option C: Smart Trigger (Hybrid)**
```yaml
# Run on every PR (frontend changes)
# Run nightly on main/develop (catch regressions)
# Manual trigger for release testing
```

**Option D: Scheduled Nightly Only**
```yaml
on:
  schedule:
    - cron: '2 4 * * *'  # 4:02 AM UTC daily
```

**Trade-offs:**

| Aspect | Option A (Every PR) | Option B (Manual) | Option C (Smart) | Option D (Nightly) |
|--------|---|---|---|---|
| **Feedback speed** | ⭐⭐⭐⭐⭐ Immediate | ⭐ Slow | ⭐⭐⭐⭐ Good | ⭐ Next day |
| **CI cost** | $$$ High | $ Low | $$ Medium | $ Low |
| **Coverage** | ✅ All PRs | ⚠️ Missed PRs | ✅ Complete | ⚠️ Gaps |
| **Flake exposure** | ⭐⭐⭐ Early | ⭐ Late | ⭐⭐⭐ Good | ⭐⭐ Late |

**My Recommendation:** **Option A (Every PR)** for MVP
- Immediate feedback to developers
- Catches regressions immediately
- Builds confidence in test suite

**Evolve to Option C (Smart)** after 6 months if CI costs become an issue.

**Your Input Needed:**
- Should tests block PR merge, or just provide information?
- Do you have CI/CD cost constraints I should know about?
- Is immediate feedback important for your workflow, or can tests run asynchronously?

---

### Q7: Team Skill Level & Onboarding

**Context:**
Different team members may have varying familiarity with E2E testing and Playwright.

**Options:**

**Option A: Minimal Training**
- Use existing Playwright conventions
- Provide copy-paste examples
- Quick onboarding for developers

**Option B: Comprehensive Documentation**
- Playbook for writing tests
- Video walk-through
- Examples for common scenarios

**Option C: Hands-On Workshop**
- Live coding session
- Pair programming on first test
- Q&A session

**My Recommendation:** **Option B (Comprehensive Docs) + Option C (Workshop)**
- Create `TESTING.md` guide with examples
- Host 30-min workshop for team
- Establish code review process for tests

**Your Input Needed:**
- Is the team already familiar with Playwright, or is this a new tool?
- Should I include video walkthrough or just written docs?
- How much time can team invest in learning the test framework (1 hour? 1 day)?

---

### Q8: Monitoring & Alerts

**Context:**
As tests run in CI, how should failures be tracked?

**Options:**

**Option A: GitHub Notifications Only (Recommended)**
- PR checks show pass/fail
- Email notifications for main branch failures
- Developer uses GitHub UI to debug

**Option B: Dashboard & Metrics**
- Central dashboard of test health
- Trend tracking (flake rate over time)
- Metrics: execution time, pass rate, etc.

**Option C: Slack Notifications**
```yaml
# On main branch failure:
# 🚨 Playwright tests failed on main
# Device list sorting test FAILED (first failure after 5 runs)
```

**Trade-offs:**

| Aspect | Option A (GitHub) | Option B (Dashboard) | Option C (Slack) |
|--------|---|---|---|
| **Setup ease** | ⭐⭐⭐⭐⭐ Native | ⭐ Complex | ⭐⭐⭐ Moderate |
| **Visibility** | ⭐⭐⭐ OK | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Good |
| **Actionability** | ⭐⭐ Requires dig | ⭐⭐⭐⭐⭐ Clear | ⭐⭐⭐⭐ Clear |
| **Cost** | Free | $-$$ | Free (if Slack-native) |

**My Recommendation:** **Option A (GitHub) + Option C (Slack) for main branch**
- GitHub checks for PR feedback
- Slack pings for main branch failures (critical)

**Your Input Needed:**
- Should test failures on main branch trigger alerts?
- Do you monitor Slack or prefer email/GitHub?
- Would trend metrics (flake rate) be useful for your team?

---

## Summary of Input Needed

| Question | Decision | Timeline |
|----------|----------|----------|
| **Q1** | Mock vs Real HA server | Before writing tests |
| **Q2** | Headless vs headed browser | Before setting up CI |
| **Q3** | Token management approach | Before configuring GitHub Actions |
| **Q4** | Fresh vs persistent test data | Before writing test factories |
| **Q5** | Test folder structure | Before writing >5 tests |
| **Q6** | CI trigger strategy | Before setting up automation |
| **Q7** | Team onboarding approach | Before team touches tests |
| **Q8** | Monitoring & alerts | Can implement after MVP |

---

## Next Steps

1. **Review** both research and recommendation documents
2. **Answer** the questions above (or in a sync/async discussion)
3. **Clarify** any ambiguous points with me before implementation
4. Once decisions made, I will:
   - Implement the directory structure
   - Create sample test files
   - Set up GitHub Actions workflow
   - Write team documentation (TESTING.md)

---

## Related Documents

- `/sessions/wizardly-stoic-cannon/mnt/vulcan-brownout/quality/ux-testing-research.md` — Framework evaluation
- `/sessions/wizardly-stoic-cannon/mnt/vulcan-brownout/quality/ux-testing-recommendation.md` — Proposed architecture

**Please share your thoughts and preferences so we can finalize the testing strategy!**


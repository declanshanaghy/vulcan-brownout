# Quality Assurance

## Current Status
- **Sprint 3**: HOLD FOR BUG FIXES (3 bugs, see SPRINT3-INDEX.md)
- **Sprint 2**: 5 critical defects identified (see quality-report.md)

## Test Infrastructure
- Integration tests: `python3 quality/scripts/test_sprint3_integration.py`
- E2E tests: `cd quality/e2e && npx playwright test`
- Deploy: `./quality/scripts/deploy.sh`
- Test entities: `./quality/scripts/setup-test-env.sh --create --count 15`

## Test Environment
HA 2026.2.2 at homeassistant.lan:8123. Credentials in .env. SSH deploy via port 2222.

## Key Docs
- SPRINT3-INDEX.md — Current bugs and test results
- EXECUTIVE-SUMMARY.md — High-level status
- ENVIRONMENT-VALIDATION.md — Staging server info + credentials
- e2e/START_HERE.md — Panel rendering bug (cursor=undefined)

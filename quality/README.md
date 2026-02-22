# Quality Assurance

## Current Status
- **Sprint 4**: SHIP IT (14/14 code checks pass, see sprint4-quality-report.md)
- **Sprint 3**: FIXED IN CODE (All 3 bugs verified resolved)
- **Sprint 2**: 5 critical defects identified (see quality-report.md)

## Test Infrastructure
- Component tests: `python3 -m pytest quality/scripts/test_component_integration.py -v`
- API integration tests: `python3 -m pytest quality/scripts/test_api_integration.py -v`
- E2E tests: `cd quality/e2e && npx playwright test`
- Deploy: `bash development/scripts/deploy.sh`
- Test entities: `./quality/scripts/setup-test-env.sh --create --count 15`

## Test Environment
HA 2026.2.2 at homeassistant.lan:8123. Credentials in .env. SSH deploy via port 2222.

## Key Docs
- **sprint4-quality-report.md** — Latest report (SHIP IT verdict)
- SPRINT3-INDEX.md — Previous sprint findings
- EXECUTIVE-SUMMARY.md — High-level status
- ENVIRONMENT-VALIDATION.md — Staging server info + credentials
- e2e/START_HERE.md — Panel rendering and test automation notes

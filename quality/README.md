# Quality — Loki (QA Tester)

This directory owns everything related to testing, deployment, and quality assurance for Vulcan Brownout.

## Environment Setup

Run once to bootstrap the full quality environment (Python venv, Playwright, secrets template):

```bash
ansible-playbook quality/ansible/setup.yml
```

See `CLAUDE.md` for prerequisites and secrets configuration.

## Running Tests

```bash
./quality/scripts/run-all-tests.sh              # All stages: lint + component + e2e
./quality/scripts/run-all-tests.sh --lint        # flake8 + mypy only
./quality/scripts/run-all-tests.sh --component   # Docker component tests only
./quality/scripts/run-all-tests.sh --e2e         # Playwright E2E mock tests only
./quality/scripts/run-all-tests.sh --docker      # Deploy + staging E2E tests
```

## Documents

- [E2E Testing Framework](e2e/README.md) — Playwright setup, test suites, commands, and architecture for the E2E layer.
- [E2E Architecture Decisions](ux-testing-decisions.md) — Recorded rulings on auth strategy, selector approach, test data, and CI integration.

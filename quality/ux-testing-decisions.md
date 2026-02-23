# E2E Testing Architecture Decisions

**By**: Loki | **Status**: IMPLEMENTED

## Rulings

1. **Staging environment**: Real HA staging instance (not mocked). Pre-provisioned entities in config.
2. **Browser**: Chromium only initially. Cross-browser in Sprint 4+.
3. **Auth**: HA long-lived access token for backend API (via YAML configuration)
3. **Auth**: HA username and password for UI login (via YAML config)
4. **Shadow DOM**: Playwright `>>` piercing selectors (`page.locator('vulcan-brownout-panel >> .selector')`).
5. **WebSocket**: Test via UI observation (verify cards update), not direct WS interception.
6. **Test data**: Static entities in staging HA configuration.yaml. No dynamic creation.
7. **CI**: GitHub Actions with Playwright container. Run on PR + nightly.
8. **Coverage priority**: Panel load → battery list rendering → threshold filtering → real-time updates → theme → empty state.

## Success Criteria
- 80%+ critical path coverage
- All tests pass in CI within 5 minutes
- Shadow DOM selectors work reliably
- Tests independent (no ordering dependency)

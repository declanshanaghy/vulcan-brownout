# Sprint 4 Plan

**Status**: Ready for implementation | **Duration**: 2 weeks | **Capacity**: 5 stories

---

## Story 4.1: Implement hass.themes.darkMode Theme Detection

- **As a**: HA user with a custom theme selected in profile
- **I want**: The Vulcan Brownout panel to respect my explicit theme choice from Home Assistant Settings
- **So that**: The panel matches the rest of HA UI automatically, without DOM sniffing

**Acceptance Criteria**:
- Panel detects `hass.themes.darkMode` on initial load and applies correct theme (light or dark)
- Theme colors transition smoothly (300ms) when user changes theme in HA Settings
- Fallback detection works if `hass.themes` unavailable: DOM data-theme → OS preference → default light
- No flickering or double-renders during theme switch
- All CSS custom properties (--vb-*) respond correctly in both light and dark modes
- Theme listener is properly cleaned up in `disconnectedCallback()` (no memory leaks)

**Technical Notes**:
- Update `vulcan-brownout-panel.js`: Add `_detect_theme()` method checking `hass.themes.darkMode` first
- Update `vulcan-brownout-panel.js`: Add `hass_themes_updated` event listener in `connectedCallback()`
- Update `vulcan-brownout-panel.js`: Call `_apply_theme()` on event fire
- Update `styles.css`: Ensure all colors use CSS custom properties (no hardcoded hex values in selectors)
- Remove or deprecate MutationObserver dark mode detection (or keep as fallback)
- Reference: `system-design.md` "Theme Detection Architecture" section

**Estimated Complexity**: M

**UX Reference**: Product Design Brief Q5, Interactions section (theme detection sequence diagram)

---

## Story 4.2: Improve Empty State Messaging

- **As a**: A new user trying Vulcan Brownout for the first time
- **I want**: Clear guidance on why no battery devices are found
- **So that**: I understand how to fix the issue (add battery_level attribute, exclude binary sensors)

**Acceptance Criteria**:
- Empty state message updates to: "No battery entities found. Check that your devices have a `battery_level` attribute and are not binary sensors. [→ Documentation]"
- Message is displayed in the main panel area when device list is empty
- Documentation link is clickable and points to HA docs or integration docs
- Message is styled consistently with light/dark theme colors
- Button layout includes Refresh, Settings, and Documentation CTA buttons
- All buttons have 44px touch target minimum

**Technical Notes**:
- Update `vulcan-brownout-panel.js`: Replace hardcoded "No battery devices found" string
- Update empty state HTML template: Add more detailed message with link
- Ensure message text respects theme colors (uses CSS custom properties)
- Keep Refresh, Settings, Documentation buttons in empty state
- Reference: Product Design Brief Q3 (Empty State Messaging section)

**Estimated Complexity**: S

**UX Reference**: Wireframes "Empty State Panel Layout"

---

## Story 4.3: Verify Scroll Performance with 150+ Devices

- **As a**: QA engineer and HA user with many battery devices
- **I want**: The infinite scroll experience to remain smooth during theme switching and pagination
- **So that**: The panel feels responsive even with large device lists

**Acceptance Criteria**:
- Scroll performance test passes with 150+ mock battery devices (no jank)
- Theme switching does NOT cause layout shifts or scroll jank (CSS transitions on colors only)
- Pagination fetch completes <500ms, new items append smoothly
- Skeleton loaders display correctly during fetch
- Back-to-top button fade-in/out is smooth (300ms)
- Card layout is consistent (no height variance between items)
- Frame rate remains >50 fps during scroll + theme transition

**Technical Notes**:
- Load test with 150+ devices in Playwright e2e test
- Measure CSS transition timing on theme change (should be 300ms, no layout recalc)
- Verify no layout shifts in device cards during append
- Check that pagination sentinel element doesn't cause scroll jank
- Reference: `system-design.md` Performance Targets section

**Estimated Complexity**: M

**UX Reference**: Product Design Brief Q1 (Scroll Performance & Infinite Scroll Feel)

---

## Story 4.4: Verify Notification Modal Discoverability & UX

- **As a**: A user managing notification preferences
- **I want**: The Notifications button to be discoverable and the modal workflow to be intuitive
- **So that**: I can easily customize my notification settings

**Acceptance Criteria**:
- [🔔 Notifications] button is visible in the panel header next to Settings
- Button is 44px+ touch target, properly labeled, and accessible
- Modal opens when button is clicked (no delay)
- Modal sections (enable toggle → frequency cap → severity filter → per-device list) flow top-to-bottom without scrolling on desktop (max-height: 80vh)
- Per-device checkbox list is scrollable if it exceeds modal height
- Save and Cancel buttons are clearly visible and functional
- Modal closes properly and settings persist (via WebSocket set_notification_preferences)
- WCAG AA accessibility: All form inputs are labeled, contrast ratios verified

**Technical Notes**:
- Update `vulcan-brownout-panel.js`: Ensure notifications modal is rendered with correct structure
- Update `styles.css`: Verify modal layout with max-height constraint
- Verify accessibility with axe-core or similar tool
- Test on mobile viewport (check button sizing and modal overflow)
- Reference: Product Design Brief Q2 (Notification Modal Discoverability)

**Estimated Complexity**: M

**UX Reference**: Wireframes "Notification Settings Modal Layout"

---

## Story 4.5: Sprint 4 Deployment

- **As a**: The QA team and deployment manager
- **I want**: A safe, idempotent deployment of Sprint 4 to the test HA server
- **So that**: All previous work (Sprint 1-3) remains stable while new features are added

**Acceptance Criteria**:
- Deployment script is idempotent (can run multiple times safely)
- Integration is deployed via SSH rsync to test HA server
- HA service is restarted after deployment
- Health check endpoint `/api/vulcan_brownout/health` returns 200 with status
- Smoke test: Panel loads, shows battery devices, theme switching works
- Rollback capability: Previous version can be restored if needed
- All 28 Sprint 3 tests continue to pass
- New Sprint 4 stories are testable after deployment

**Technical Notes**:
- Update `deployment/deploy.sh` script to handle frontend assets (vulcan-brownout-panel.js, styles.css)
- Ensure .gitignore excludes `.env` file (secrets not committed)
- Use idempotent rsync flags: `rsync -av --delete`
- Verify symlink release strategy (keep previous release accessible for rollback)
- Restart HA: `systemctl restart homeassistant` (via SSH) or use HA API restart endpoint
- Health check: `curl -k https://$HA_URL:$HA_PORT/api/vulcan_brownout/health`
- Smoke test steps: Navigate to panel, verify data loads, toggle HA theme, check colors change smoothly
- Reference: `architecture/adrs/ADR-003-deployment-architecture.md`

**Estimated Complexity**: M

**UX Reference**: N/A (infrastructure story)

---

## Dependencies & Recommended Order

1. **Story 4.1** (Theme Detection) — Core feature, enables other stories. Start first.
2. **Story 4.2** (Empty State Messaging) — Independent, can run in parallel with 4.1.
3. **Story 4.3** (Scroll Performance) — Verification story, run after 4.1-4.2 complete.
4. **Story 4.4** (Notification Modal UX) — Independent verification, run after 4.1-4.2 complete.
5. **Story 4.5** (Deployment) — Final integration and deployment. Run last.

---

## Definition of Done (Per Story)

- [ ] Code changes implemented per specification
- [ ] Technical notes and patterns followed (per system-design.md)
- [ ] Unit tests pass (if applicable for JavaScript)
- [ ] Playwright E2E tests pass (Loki runs test suite)
- [ ] No console errors or warnings
- [ ] Accessibility verified (WCAG AA, 44px touch targets)
- [ ] Code reviewed by Architect (FiremanDecko)
- [ ] QA acceptance confirmed (Loki)

---

## Success Criteria for Sprint 4

- [ ] 5/5 stories implemented and QA-passed
- [ ] All Sprint 3 tests continue to pass (28/28)
- [ ] Theme switching works smoothly (no flicker, <300ms visible transition)
- [ ] Empty state messaging is clear and helpful
- [ ] Scroll performance remains smooth (no jank with 150+ devices)
- [ ] Notification modal is discoverable and functional
- [ ] Deployment to test HA server is clean and reversible
- [ ] No regressions from Sprint 3 features

---

## Future Backlog (Sprint 5+)

- Battery degradation trend graphs
- Notification scheduling with quiet hours
- Bulk device operations (enable/disable all)
- Multi-language internationalization
- Advanced filtering (by device type, room)
- CSV/JSON export of device data
- Mobile app deep linking

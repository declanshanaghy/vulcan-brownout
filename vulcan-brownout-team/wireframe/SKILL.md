---
name: vulcan-brownout-wireframe
description: "WireMD wireframe standard for the Vulcan Brownout project. Defines how all UX wireframes (panel layouts, form mockups, component mockups) must be authored using WireMD markdown syntax. Software flow diagrams, state machines, and architecture diagrams continue to use Mermaid. Use this reference whenever producing or reviewing wireframes."
---

# Vulcan Brownout Wireframe Standard — WireMD

All **UX wireframes** in this project use **WireMD** syntax.
All **software diagrams** (flows, state machines, component relationships, architecture) use **Mermaid** syntax.

Do not mix them. The distinction is:
- **WireMD** → panel layouts, form mockups, component mockups, UI structure
- **Mermaid** → user flows, state transitions, architecture, data flow, sequence diagrams

---

## WireMD Quick Reference

WireMD transforms plain markdown into visual wireframes. It produces valid CommonMark that degrades gracefully as plain text. Output styles: `sketch`, `clean`, `wireframe`, `tailwind`, `material`, `brutal`.

### Core Elements

| Syntax | Renders as |
|--------|------------|
| `# Heading` | Page/panel title |
| `## Section` | Section heading (can attach `.grid-N` for columns) |
| `[Button Text]` | Secondary button |
| `[Button Text]*` | Primary button |
| `[Label_________]` | Text input field |
| `[Password______]` / `[***]` | Password input |
| `[ ]` / `[x]` | Unchecked / checked checkbox |
| `( )` / `(•)` | Radio unselected / selected |
| `[[ A \| B \| C ]]` | Navigation bar or horizontal tab bar |
| `[Select_______v]` | Dropdown |
| `:icon-name:` | Icon (e.g., `:battery:`, `:check:`, `:warning:`) |
| `---` | Horizontal divider |
| `> text` | Emphasized/callout block |

### Attribute Modifiers (curly braces)

```
[Input___]{type:email required}   ← HTML attributes
## Section {.grid-3}              ← 3-column grid layout
[Button]* {.danger}               ← CSS class modifier
{:disabled}                       ← State indicator
```

### Containers

```
::: card
Content inside a card
:::

::: modal
## Modal Title
Content
[Cancel] [Confirm]*
:::
```

---

## Vulcan Brownout Conventions

### File Location

Wireframes are saved to `design/wireframes.md`. Each sprint overwrites the previous content — git tracks history.

### Wireframe Header

Every wireframe block must start with a header comment:

```
<!-- Wireframe N: Title — By Luna | Sprint 6 | 2026-02-23 -->
```

### HA Panel Conventions

The Vulcan Brownout panel is a sidebar panel inside Home Assistant. Use these structural conventions:

```
[[ 🔋 Battery Monitoring | Connected 🟢 ]]

[[ Low Battery | Unavailable Devices ]]

---

| Last Seen | Device | Area | Model | % |
|-----------|--------|------|-------|---|
| 2m ago    | Front Door Lock | Entrance | Schlage BE469 | 8% |
| 5m ago    | Motion Sensor   | Kitchen  | Aqara MS-S02  | 12% |

---

> No more devices to load.
```

Use standard markdown tables for entity rows — WireMD renders them cleanly. For badge/pill components, use inline `[text]{.badge}`.

### Status Badges

```
[unavailable]{.badge}   ← grey pill
[unknown]{.badge}       ← grey pill
[critical]{.badge-red}  ← red pill (future)
```

### Tab Bar

```
[[ Low Battery* | Unavailable Devices ]]
```

The `*` denotes the active tab in wireframe notation. In the actual implementation, the active class is controlled by `_activeTab`.

### Empty States

```
> :battery: **All batteries above 15%**
> No low battery devices found.

> :check: **No unavailable devices.**
> All monitored devices are responding.
```

---

## Full Panel Wireframe Example — Low Battery Tab

```wiremd
<!-- Wireframe 17: Low Battery Tab Active — Luna | Sprint 6 -->

# 🔋 Battery Monitoring

[[ Low Battery* | Unavailable Devices ]]

---

| Last Seen | Device | Area | Mfr / Model | % |
|-----------|--------|------|-------------|---|
| 2m ago | Front Door Lock | Entrance | Schlage BE469 | **8%** |
| 5m ago | Motion Sensor Kitchen | Kitchen | Aqara MS-S02 | **12%** |
| 8m ago | Patio Door Sensor | Outside | Sonoff SNZB-04 | **14%** |
```

---

## Full Panel Wireframe Example — Unavailable Devices Tab

```wiremd
<!-- Wireframe 18: Unavailable Devices Tab Active — Luna | Sprint 6 -->

# 🔋 Battery Monitoring

[[ Low Battery | Unavailable Devices* ]]

---

| Last Seen | Device | Area | Mfr / Model | Status |
|-----------|--------|------|-------------|--------|
| 1h ago | Garage Door Sensor | Garage | Aqara | [unavailable]{.badge} |
| 3h ago | Back Door Lock | Yard | Schlage | [unknown]{.badge} |
| 6h ago | Attic Humidity Sensor | Attic | Sonoff | [unavailable]{.badge} |
```

---

## Full Panel Wireframe Example — Empty States

```wiremd
<!-- Wireframe 19a: Low Battery Empty State — Luna | Sprint 6 -->

# 🔋 Battery Monitoring

[[ Low Battery* | Unavailable Devices ]]

---

> :battery: **All batteries above 15%**
> No low battery devices found.
```

```wiremd
<!-- Wireframe 19b: Unavailable Empty State — Luna | Sprint 6 -->

# 🔋 Battery Monitoring

[[ Low Battery | Unavailable Devices* ]]

---

> :check: **No unavailable devices.**
> All monitored devices are responding.
```

---

## Tooling

### CLI (live preview)
```bash
npx wiremd serve design/wireframes.md   # live preview in browser
npx wiremd build design/wireframes.md   # export to HTML
npx wiremd build design/wireframes.md --format react   # export to React JSX
```

### VS Code Extension
Search for **WireMD** in the VS Code extension marketplace for syntax highlighting and in-editor preview.

### Website
[wiremd.dev](https://wiremd.dev) — online editor and documentation.

---

## What WireMD Is NOT Used For

Do not use WireMD for:
- Architecture diagrams → use Mermaid `graph TD`
- User flow / state machines → use Mermaid `stateDiagram-v2`
- Component relationship diagrams → use Mermaid `graph TD`
- Sequence diagrams → use Mermaid `sequenceDiagram`
- Kanban boards → use Mermaid `graph LR`

All software diagrams must follow `vulcan-brownout-team/ux-assets/mermaid-style-guide.md`.

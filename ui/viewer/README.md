# Control Board Viewer

## Overview
A read-only, single-file HTML viewer for sf_packet artifacts. No build step, no dependencies, no external network requests.

**Version:** 0.2

## How to Open

### Option 1: Local file (simple)
Open `ui/viewer/index.html` directly in your browser.

**Note:** Due to browser security policies, fetching local JSON files may be blocked. Use Option 2 if tables don't load.

### Option 2: Local server (recommended)
From the repository root, run:

```bash
python3 -m http.server 8080
```

Then open: http://localhost:8080/ui/viewer/index.html

## Artifacts Read

The viewer reads sf_packet JSON files in this order:

| Priority | Path | Description |
|----------|------|-------------|
| 1 | `out/sf_packet.preview.json` | Generated preview output |
| 2 | `examples/expected_outputs/sf_packet.example.json` | Fallback example data |

Paths are relative to the repository root.

## Features

### Toolbar

The toolbar provides quick access to common commands:

| Button | Command |
|--------|---------|
| Validate | Validate configuration files (base + patch) |
| Preview Baseline | Generate preview with baseline example data |
| Preview Edge | Generate preview with edge case data |
| Smoke Baseline | Run smoke test against baseline expected output |
| Smoke Edge | Run smoke test against edge expected output |

**Copy-Only Default:** Clicking any toolbar button opens a modal displaying the full command. The default action is to **copy the command to clipboard**.

**Confirm-Run Gate:** To enable the "Run" button, you must first check the **"I CONFIRM RUN"** checkbox in the toolbar. Even when enabled, execution is not available in the browser environment - you must paste and run the command in your terminal.

Commands are stored in `run_commands.json` and can be customized.

### Filters

Located below the toolbar, filters allow you to narrow down table results:

| Filter | Description |
|--------|-------------|
| **Search** | Free-text search across all fields in all tables |
| **Severity Chips** | Toggle visibility of blocking/warning/info severity rows |
| **Status Chips** | Toggle visibility of ready/needs_review/blocked status rows |
| **Subtype Dropdown** | Filter Contract Results by detected_subtype |

Filters apply across all three tables. Click a chip to toggle it on/off (inactive chips appear faded).

### Drilldown Drawer

Click any row in any table to open a slide-out drawer on the right side. The drawer displays:

- **Full record JSON**: The complete data object for that row
- **Copy JSON button**: Copy the JSON to clipboard for use elsewhere

Press `Escape` or click outside the drawer to close it.

### Summary Cards
Displays counts from `sf_summary`:
- Total contracts
- Ready (green)
- Needs Review (orange)
- Blocked (red)

### Tables
Three tables with deterministic sorting:

1. **Contract Results** - `sf_contract_results`
   - Sorted by: contract_key (nulls last), file_url (nulls last), file_name (nulls last)

2. **Issues** - `sf_issues`
   - Sorted by: join triplet (nulls last), then severity (blocking > warning > info), then sheet, field

3. **Field Actions** - `sf_field_actions`
   - Sorted by: join triplet (nulls last), then severity (blocking > warning > info), then sheet, field

### Diff Pane
Instructions for running the smoke test to verify determinism:
```bash
bash scripts/replit_smoke.sh
```

The viewer does NOT execute commands automatically.

## Swapping Artifacts

To view different data, either:
1. Generate new preview: `python3 local_runner/run_local.py --base ... --out out/sf_packet.preview.json`
2. Copy your JSON to `out/sf_packet.preview.json`
3. Edit `sample_data_links.json` and modify the viewer to use different paths

## Files

| File | Description |
|------|-------------|
| `index.html` | The viewer (single file, no build step) |
| `run_commands.json` | Canonical commands for toolbar buttons |
| `sample_data_links.json` | Documented artifact paths |
| `README.md` | This file |

## Technical Details

- **No build step**: Open index.html directly
- **No dependencies**: Vanilla HTML, CSS, JavaScript
- **No network requests**: All data loaded from local filesystem
- **Deterministic display**: Sorting matches run_local.py output ordering
- **Keyboard shortcuts**: Press `Escape` to close modals and drawers

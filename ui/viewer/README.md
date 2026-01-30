# Control Board Viewer

## Overview
A read-only, single-file HTML viewer for sf_packet artifacts. No build step, no dependencies, no external network requests.

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

### Summary Cards
Displays counts from `sf_summary`:
- Total contracts
- Ready (green)
- Needs Review (orange)
- Blocked (red)

### Tables
Three tables with deterministic sorting:

1. **Contract Results** - `sf_contract_results`
   - Sorted by: contract_key (present first), file_url, file_name

2. **Issues** - `sf_issues`
   - Sorted by: severity (blocking > warning > info), then join triplet

3. **Field Actions** - `sf_field_actions`
   - Sorted by: severity (blocking > warning > info), then join triplet

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

## Technical Details

- **No build step**: Open index.html directly
- **No dependencies**: Vanilla HTML, CSS, JavaScript
- **No network requests**: All data loaded from local filesystem
- **Deterministic display**: Sorting matches run_local.py output ordering

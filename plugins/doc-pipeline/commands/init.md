---
description: Initialize a new documentation project by scaffolding the pipeline for a target docs URL. Use when the user says "init", "bootstrap", "set up pipeline for", or wants to start a new doc project from a URL.
argument-hint: <docs-url> [--board <name>] [--tab <name>]
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, WebFetch, AskUserQuestion]
---

# Documentation Pipeline Initializer

Analyze a documentation site and generate everything needed to run the doc-pipeline: `discover.py`, `fetch.py`, test fixtures, test suite, and prompts.

## Arguments

$ARGUMENTS

Parse the arguments for:
- **docs-url** (required): the target documentation URL to scaffold a fetcher for
- **--board name** (optional): board/product name for tab selection and title templates
- **--tab name** (optional): specific tab label to select on pages with variant tabs
- **--section-name name** (optional): override the section name (default: derived from URL)

If no URL is provided, ask the user for one.

## Workflow

Execute these 9 steps sequentially. Do NOT skip steps. Present results to the user at checkpoints (steps 2, 8).

---

### Step 1: Parse Arguments & Validate Project

1. Extract `url`, `--board`, `--tab`, and `--section-name` from the arguments.
2. Check if `docs/lib/discover.py` already exists in the project. If it does, ask the user via AskUserQuestion whether to overwrite or abort.
3. Create the project directory structure:

```bash
mkdir -p docs/{lib,prompts,sections,tests/fixtures}
```

4. Create `docs/lib/__init__.py` if it doesn't exist (empty file).

---

### Step 2: Fetch & Analyze Target URL

Use Bash with Python to fetch the raw HTML and detect the site framework. Run this script:

```bash
python3 -c "
import requests
from bs4 import BeautifulSoup
import json

url = '<TARGET_URL>'
resp = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
resp.raise_for_status()
soup = BeautifulSoup(resp.text, 'html.parser')

result = {
    'status_code': resp.status_code,
    'title': soup.title.string if soup.title else None,
    'has_sidebar': False,
    'framework': 'unknown',
    'signals': [],
}

# Check meta generator
gen = soup.find('meta', attrs={'name': 'generator'})
if gen and gen.get('content'):
    result['signals'].append(f'meta generator: {gen[\"content\"]}')

# Check for framework-specific indicators in full HTML
html_text = resp.text

# Docusaurus
if '__DOCUSAURUS' in html_text or 'docusaurus' in html_text.lower():
    result['framework'] = 'docusaurus'
    result['signals'].append('Docusaurus JS global or reference found')
if soup.select('.theme-doc-sidebar-menu'):
    result['has_sidebar'] = True
    result['signals'].append('Docusaurus sidebar class found')

# Sphinx / ReadTheDocs
if 'READTHEDOCS_DATA' in html_text or 'rst-content' in html_text:
    result['framework'] = 'sphinx'
    result['signals'].append('Sphinx/RTD indicator found')
if soup.select('.rst-content') or soup.select('.toctree-wrapper'):
    result['has_sidebar'] = True
    result['signals'].append('Sphinx toctree or rst-content found')

# GitBook
if 'gitbook' in html_text.lower():
    result['framework'] = 'gitbook'
    result['signals'].append('GitBook reference found')
if soup.select('.gitbook-root'):
    result['has_sidebar'] = True
    result['signals'].append('GitBook root class found')

# Generic sidebar detection
if not result['has_sidebar']:
    navs = soup.select('nav ul li a')
    asides = soup.select('aside ul li a')
    if len(navs) > 5 or len(asides) > 5:
        result['has_sidebar'] = True
        result['signals'].append(f'Generic sidebar: {len(navs)} nav links, {len(asides)} aside links')

# Tab detection
tabs = soup.select('[role=\"tab\"], .tabs__item, .tabbed-set label, [data-tab]')
if tabs:
    tab_labels = [t.get_text(strip=True) for t in tabs[:20]]
    result['tabs_found'] = tab_labels
    result['signals'].append(f'Tabs detected: {tab_labels[:10]}')

print(json.dumps(result, indent=2))
"
```

Replace `<TARGET_URL>` with the actual URL from the arguments.

**Interpret the results using this decision tree:**

```
Has sidebar navigation?
├─ YES → Identify framework
│  ├─ Docusaurus  → sidebar DOM walker
│  ├─ Sphinx/RTD  → toctree parser
│  ├─ GitBook     → JSON endpoint
│  └─ Unknown     → heuristic: deepest <nav>/<ul> with internal links
│
└─ NO → Identify content organization
   ├─ Single page with heading sections → split by <h2>/<h3>
   ├─ Index page with subpage links     → extract <a> hrefs from main content
   ├─ API/JS-rendered content           → find JSON endpoint or flag ACTION
   └─ No recognizable pattern           → manual scaffold + ACTION alert
```

**Present the detection results to the user via AskUserQuestion:**
- Show: framework detected, sidebar presence, signals found, tab labels (if any)
- Options: "Confirmed — proceed", "Wrong framework — it's actually [X]", "Abort"

If the HTML body is empty or very small (< 500 chars of text content), this is likely a JS-rendered site. Raise an ACTION alert and ask the user how to proceed.

---

### Step 3: Capture Test Fixtures

1. Save the sidebar/navigation HTML to `docs/tests/fixtures/sidebar.html`:
   - For Docusaurus: extract the `<nav>` or `.theme-doc-sidebar-menu` element
   - For Sphinx: extract the `.toctree-wrapper` or sidebar `<nav>`
   - For GitBook: extract the sidebar container
   - For unknown: extract the largest `<nav>` or `<aside>` element
   - If no sidebar: save the main content area instead

2. Fetch one child page (pick the first link from the sidebar/navigation that isn't the current page) and save its full HTML to `docs/tests/fixtures/sample-page.html`.

Use Bash + Python with requests/BeautifulSoup for both fetches. Save the raw HTML, not processed content.

---

### Step 4: Copy Template Files

1. Find the plugin's template directory:

```
Glob("**/plugins/doc-pipeline/templates/*")
```

2. Copy template files to the project:

| Template Source | Destination |
|----------------|-------------|
| `templates/cache.py` | `docs/lib/cache.py` |
| `templates/pipeline.py` | `docs/pipeline.py` |
| `templates/scout.md` | `docs/prompts/scout.md` |
| `templates/processor.md` | `docs/prompts/processor.md` |
| `templates/auditor.md` | `docs/prompts/auditor.md` |

Read each template file and Write it to the destination.

3. **Customize pipeline.py** if `--board` or `--tab` was provided:
   - If `--tab` was given: edit the `argparse` default for `--tab` from `None` to the provided value
   - If `--board` was given: update the description string to include the board name

4. **Customize processor.md** if `--board` was provided:
   - Replace `{Section Title} — Reference` with `{Section Title} — {board} Reference`

---

### Step 5: Generate `docs/lib/discover.py` (AI-Driven)

Based on the framework detected in Step 2 and the sidebar fixture from Step 3, **write `docs/lib/discover.py` from scratch**.

Read the sidebar fixture first (`docs/tests/fixtures/sidebar.html`) to understand the actual DOM structure.

**Requirements:**
- Must implement: `def discover_pages(section_url: str) -> list[dict]:`
- Each dict must have: `{"title": str, "url": str, "slug": str, "depth": int}`
- Slugs must be filesystem-safe (lowercase, hyphens, no spaces or special chars)
- All URLs must be absolute (start with `https://`)
- Depth: root-level children are depth 0, their children depth 1, etc.
- Only uses: `requests`, `beautifulsoup4`, stdlib
- NO headless browser dependencies

**Framework-specific strategies:**
- **Docusaurus**: Walk `.theme-doc-sidebar-menu` or equivalent sidebar DOM. Follow nested `<ul>` for depth.
- **Sphinx**: Parse `.toctree-wrapper` or `<nav>` with `toctree` links. Handle relative URLs.
- **GitBook**: Try JSON API endpoint first (`/~gitbook/api/...`), fall back to sidebar DOM.
- **Unknown with sidebar**: Find the deepest `<nav>` or `<ul>` containing internal links. Extract `<a>` hrefs.
- **No sidebar**: Extract links from main content area, or split by headings if single page.

Generate a slug from each title: lowercase, replace spaces/special chars with hyphens, strip leading/trailing hyphens.

---

### Step 6: Generate `docs/lib/fetch.py` (AI-Driven)

Based on the framework and the sample page fixture from Step 3, **write `docs/lib/fetch.py` from scratch**.

Read the sample page fixture first (`docs/tests/fixtures/sample-page.html`) to understand the actual page structure.

**Requirements:**
- Must implement:
  - `def fetch_page(url: str, tab_label: str | None = None) -> str:` — returns clean markdown
  - `def fetch_all(pages: list[dict], output_dir: str, tab_label: str | None = None) -> list[str]:` — fetches all, returns saved paths
- Only uses: `requests`, `beautifulsoup4`, `markdownify`, stdlib
- NO headless browser dependencies

**fetch_page must:**
1. Fetch the URL with requests
2. Parse with BeautifulSoup
3. Extract the main content area (framework-specific selector):
   - Docusaurus: `article` or `.theme-doc-markdown`
   - Sphinx: `.rst-content` or `[role="main"]`
   - GitBook: `.page-inner` or `main`
   - Unknown: `main`, `article`, or largest content `<div>`
4. Strip navigation chrome: breadcrumbs, sidebar fragments, "Edit this page" links, pagination, footer
5. Handle board/variant tabs if `tab_label` is provided:
   - Find tab containers, select the matching tab's content panel
   - If the target tab isn't found, include all content and log a warning
6. Convert admonitions (note/warning/caution blocks) to GitHub-style alert syntax
7. Convert HTML to markdown using `markdownify`
8. Clean up: strip excessive whitespace, fix markdownify artifacts (`\_` → `_`)

**fetch_all must:**
1. Create `output_dir` if it doesn't exist
2. Iterate over pages, call `fetch_page` for each
3. Save markdown to `output_dir/{slug}.md`
4. Print progress as it goes
5. Return list of saved file paths

---

### Step 7: Generate Test Suite

Write two test files based on the spec. Tests must run against the saved fixtures (offline, deterministic).

#### `docs/tests/test_discover.py`

```python
"""Tests for discover.py — runs against sidebar fixture."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
import pytest

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "sidebar.html")
SECTION_URL = "<TARGET_URL>"  # Replace with actual URL

@pytest.fixture
def sidebar_html():
    with open(FIXTURE_PATH) as f:
        return f.read()

@pytest.fixture
def pages(sidebar_html):
    """Mock requests.get to return the sidebar fixture, then call discover_pages."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = sidebar_html
    mock_resp.raise_for_status = MagicMock()
    with patch("lib.discover.requests.get", return_value=mock_resp):
        from lib.discover import discover_pages
        return discover_pages(SECTION_URL)

def test_page_count(pages):
    """Verify a reasonable number of pages were discovered."""
    assert len(pages) >= 1, "Should discover at least 1 page"
    assert len(pages) <= 200, f"Suspiciously high page count: {len(pages)}"

def test_slugs_are_filesystem_safe(pages):
    """Slugs must contain only lowercase alphanumeric chars and hyphens."""
    import re
    for p in pages:
        assert re.match(r'^[a-z0-9][a-z0-9-]*$', p['slug']), \
            f"Unsafe slug: {p['slug']}"

def test_urls_are_absolute(pages):
    """All URLs must be absolute."""
    for p in pages:
        assert p['url'].startswith('https://') or p['url'].startswith('http://'), \
            f"Relative URL found: {p['url']}"

def test_depth_values_consistent(pages):
    """Depth must be >= 0 and root children should be depth 0."""
    for p in pages:
        assert p['depth'] >= 0, f"Negative depth: {p}"
    if pages:
        assert min(p['depth'] for p in pages) == 0, "No root-level pages found"

def test_no_duplicate_slugs(pages):
    """Each slug must be unique."""
    slugs = [p['slug'] for p in pages]
    assert len(slugs) == len(set(slugs)), \
        f"Duplicate slugs: {[s for s in slugs if slugs.count(s) > 1]}"
```

Replace `<TARGET_URL>` with the actual URL from the arguments.

#### `docs/tests/test_fetch.py`

```python
"""Tests for fetch.py — runs against sample page fixture."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
import pytest

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "sample-page.html")
SAMPLE_URL = "<SAMPLE_PAGE_URL>"  # Replace with actual child page URL

@pytest.fixture
def page_html():
    with open(FIXTURE_PATH) as f:
        return f.read()

@pytest.fixture
def markdown_output(page_html):
    """Mock requests.get to return the fixture, then call fetch_page."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = page_html
    mock_resp.content = page_html.encode()
    mock_resp.raise_for_status = MagicMock()
    with patch("lib.fetch.requests.get", return_value=mock_resp):
        from lib.fetch import fetch_page
        return fetch_page(SAMPLE_URL)

def test_returns_markdown_not_html(markdown_output):
    """Output should not contain raw HTML structural tags."""
    for tag in ['<div', '<span', '<nav', '<header', '<footer']:
        assert tag not in markdown_output, \
            f"HTML tag found in markdown output: {tag}"

def test_strips_navigation_chrome(markdown_output):
    """No breadcrumbs, sidebar text, or edit links."""
    chrome_markers = ['Edit this page', 'Previous', 'Next', 'breadcrumb']
    lower = markdown_output.lower()
    for marker in chrome_markers:
        assert marker.lower() not in lower, \
            f"Navigation chrome found: {marker}"

def test_preserves_code_blocks(markdown_output):
    """If the source has code, fenced code blocks should survive."""
    # This test passes if there are no code blocks in the source
    # It fails if source has <pre>/<code> but output has no ```
    if '```' not in markdown_output:
        # Verify source also had no code
        with open(FIXTURE_PATH) as f:
            html = f.read()
        if '<pre' in html or '<code' in html:
            pytest.fail("Source has code blocks but markdown output has none")

def test_board_tab_selection(page_html):
    """If tabs exist and tab_label is given, only that tab's content appears."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = page_html
    mock_resp.content = page_html.encode()
    mock_resp.raise_for_status = MagicMock()
    with patch("lib.fetch.requests.get", return_value=mock_resp):
        from lib.fetch import fetch_page
        # Should not raise even if no tabs present
        result = fetch_page(SAMPLE_URL, tab_label="NonexistentTab")
        assert len(result) > 0, "Should return content even with wrong tab label"

def test_output_has_substance(markdown_output):
    """Markdown must have meaningful content (catches empty JS-rendered pages)."""
    assert len(markdown_output.strip()) > 100, \
        f"Output too short ({len(markdown_output.strip())} chars) — possible JS rendering issue"
```

Replace `<SAMPLE_PAGE_URL>` with the actual child page URL discovered in Step 3.

**IMPORTANT:** Adapt the test assertions based on what you actually observed in the fixtures. For example:
- If the sample page has no code blocks, adjust `test_preserves_code_blocks` accordingly
- If the site has no tabs, `test_board_tab_selection` should just verify no crash
- Set a reasonable expected page count range for `test_page_count`

---

### Step 8: Run Tests & Generate Report

1. Run the test suite:

```bash
cd <project_root> && python -m pytest docs/tests/ -v 2>&1
```

2. **Evaluate alert conditions** based on results:

**WARN conditions (log but don't block):**
- Page count < 3 or > 100
- Tab structure found but `--tab` board not in tab list
- Markdown size < 20% of HTML size
- Sidebar nesting > 3 levels

**ACTION conditions (block pipeline):**
- Any test fails
- No sidebar and no content organization detected
- HTTP 401/403 when fetching
- Empty body after fetch (JS-rendered)

3. Write `docs/generation-report.md` with:
   - Framework detection results and rationale
   - Full page list from discover_pages
   - Alert summary (all WARNs and ACTIONs)
   - Fixture checksums (MD5 of sidebar.html and sample-page.html)
   - Test results

4. **Present the alert summary to the user.** Format:

```
=== Fetcher Generation Complete ===

  discover.py  ✓ generated
  fetch.py     ✓ generated
  fixtures/    ✓ 2 snapshots saved
  tests/       ✓ N tests passed (or ✖ N failed)

  ⚠ WARN: [description]
  ✖ ACTION: [description]  ← blocks pipeline

  [Next steps]
```

---

### Step 9: Smoke Test (if all tests pass)

Only run this step if ALL tests passed in Step 8.

1. Run a real fetch to verify the generated code works end-to-end:

```bash
cd <project_root> && python docs/pipeline.py <TARGET_URL> --section-name test-run
```

Add `--tab <tab>` if a tab was specified.

2. Verify output files exist in `docs/sections/test-run/raw/`.

3. Clean up the smoke test:

```bash
rm -rf docs/sections/test-run/
```

4. If the smoke test fails:
   - Read the error output
   - Fix the generated code (`discover.py` or `fetch.py`)
   - Re-run tests (Step 8)
   - Retry the smoke test (up to 3 attempts total)
   - If still failing after 3 attempts, raise an ACTION alert and stop

---

## Alert Reference

### WARN Triggers
- Unusual framework version detected
- Page count outside range (< 3 or > 100)
- Tab structure found but target board not in tab list
- Non-200 responses during fixture capture
- Markdown size < 20% of HTML size (possible JS rendering)
- Sidebar nesting depth > 3 levels

### ACTION Triggers
- No sidebar and no recognizable content organization
- HTTP 401/403 (authentication required)
- Empty body after fetch (JS-rendered, needs headless browser)
- Multiple conflicting navigation structures
- Any test in the generated suite fails
- Framework detected but no matching template exists

## Constraints

- **No headless browser** — do not use Playwright, Selenium, or puppeteer. If JS rendering is required, raise an ACTION alert.
- **Fixtures must be committed** — tests run offline against saved HTML snapshots.
- **Dependencies**: only `requests`, `beautifulsoup4`, `markdownify`, and stdlib.
- **Function signatures are non-negotiable** — `discover_pages`, `fetch_page`, `fetch_all` must match the spec exactly.

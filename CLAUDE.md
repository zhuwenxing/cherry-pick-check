# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A CLI tool to check if GitHub PRs have been cherry-picked to release branches. Designed for milvus-io/milvus repository workflows but works with any GitHub repository that follows similar cherry-pick conventions.

## Development Commands

```bash
# Setup environment
uv venv -p 3.10
source .venv/bin/activate

# Install dependencies
uv pip install -e .

# Run the CLI
cherry-pick-check <username>
cherry-pick-check <username> -r owner/repo -b master -t 2.4 -t 2.5

# Run with verbose output
cherry-pick-check <username> -v
```

## Architecture

The codebase follows a modular design in `src/cherry_pick_check/`:

```
src/cherry_pick_check/
├── __init__.py           # Package entry point, exports main()
├── cli.py                # Click-based CLI, orchestrates workflow
├── auth.py               # GitHub authentication (gh CLI / GITHUB_TOKEN)
├── github_client.py      # HTTP client with pagination and rate limiting
├── cherry_pick_detector.py  # Core detection logic
├── branch_detector.py    # Release branch auto-detection
├── models.py             # Pydantic data models
└── output.py             # Rich-based table formatting
```

### Module Details

#### cli.py
Entry point using Click framework. Orchestrates the entire workflow:
1. Authenticate with GitHub
2. Fetch user's PRs from source branch
3. Detect/filter target branches
4. Run cherry-pick detection
5. Display results table

Key function: `cli()` - decorated with `@click.command()`, handles all CLI options.

#### auth.py
Authentication flow:
1. Try `gh auth token` subprocess call
2. Fall back to `GITHUB_TOKEN` environment variable
3. Raise `AuthenticationError` with detailed setup instructions if both fail

#### github_client.py
`GitHubClient` class with httpx:
- `get_user_prs(repo, author, base_branch, since)` - Search API for user's PRs (merged + open)
- `search_related_prs(repo, pr_number)` - Find PRs referencing a specific PR number
- `get_pr_details(repo, pr_number)` - Get full PR details including base branch
- `get_branches(repo)` - List all repository branches
- `_handle_rate_limit()` - Auto-wait up to 2 minutes on rate limit, or raise `RateLimitError`

#### cherry_pick_detector.py
`CherryPickDetector` class:
- `get_user_prs()` - Wraps GitHubClient, returns `list[PRInfo]`
- `detect_cherry_picks()` - Main detection with progress bar
- `_detect_for_pr()` - Per-PR detection logic

Helper functions:
- `_is_cherry_pick_reference(body, pr_number)` - Pattern matching for cherry-pick indicators
- `_parse_pr_state(pr_data)` - Extract PRState from API response
- `_parse_pr_info(pr_data)` - Convert API response to PRInfo model

#### branch_detector.py
Version-aware branch detection:
- `detect_release_branches(branches, exclude, major_only)` - Filter and sort release branches
- `filter_branches(all_branches, targets)` - Validate user-specified branches exist
- `_parse_version(branch)` - Parse "2.4.x" → (2, 4)
- `_version_compare(a, b)` - Semantic version comparison

Supported patterns: `2.4`, `2.4.1`, `2.x`, `2.4.x`

#### models.py
Pydantic models:
```python
class PRState(str, Enum):
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"

class CherryPickStatus(str, Enum):
    PICKED = "picked"
    NOT_PICKED = "not_picked"
    UNKNOWN = "unknown"

class PRInfo(BaseModel):
    number: int
    title: str
    url: str
    author: str
    state: PRState
    created_at: datetime | None
    merged_at: datetime | None
    base_branch: str

class CherryPickResult(BaseModel):
    source_pr: PRInfo
    target_branch: str
    status: CherryPickStatus
    related_pr: PRInfo | None
    detection_method: str
```

#### output.py
Rich library formatting:
- `print_results_table(results, console)` - Main table output
- `_format_pr_state(state)` - Color-coded state (yellow/green/dim)
- `_format_cp_cell(result)` - Cherry-pick status cell with links
- `_truncate(text, max_len)` - Text truncation with ellipsis

## Data Flow

```
1. CLI parses arguments
         ↓
2. auth.get_github_token()
         ↓
3. GitHubClient.get_user_prs() → GitHub Search API
         ↓
4. branch_detector.detect_release_branches() → GitHub Branches API
         ↓
5. CherryPickDetector.detect_cherry_picks()
   └── For each source PR:
       └── GitHubClient.search_related_prs() → Find referencing PRs
       └── _is_cherry_pick_reference() → Pattern matching
       └── GitHubClient.get_pr_details() → Get target branch
         ↓
6. output.print_results_table() → Rich formatted output
```

## Cherry-Pick Detection Strategy

The detector searches for PRs that reference a source PR number in their body using patterns like:
- `#12345` or `pr: #12345`
- `https://github.com/owner/repo/pull/12345`
- Keywords: "cherry-pick", "backport", "pick pr"

Pattern matching logic in `_is_cherry_pick_reference()`:
1. Check for cherry-pick keywords (cherry-pick, backport, pick pr)
2. Check for PR number reference in various formats
3. Special case: `pr:` prefix with reference = cherry-pick (milvus workflow)

This matches the milvus-io/milvus workflow where cherry-pick PRs include "Cherry-pick from master\npr: #XXXXX" in the body.

## Error Handling

- `AuthenticationError` - No valid GitHub credentials found
- `RateLimitError` - GitHub API rate limit exceeded (auto-waits up to 2 minutes)
- Generic exceptions caught in CLI with optional traceback in verbose mode

## Authentication

Requires GitHub authentication. The tool tries these methods in order:
1. `gh auth token` (GitHub CLI)
2. `GITHUB_TOKEN` environment variable

## Dependencies

- **httpx** - HTTP client for GitHub API calls
- **click** - CLI framework
- **rich** - Terminal formatting and progress bars
- **pydantic** - Data validation and models

## Extension Points

To add new detection patterns:
- Edit `CHERRY_PICK_KEYWORDS` list in `cherry_pick_detector.py`
- Modify `_is_cherry_pick_reference()` for new body patterns

To add new branch patterns:
- Edit `RELEASE_BRANCH_PATTERNS` in `branch_detector.py`

To customize output:
- Modify `print_results_table()` in `output.py`

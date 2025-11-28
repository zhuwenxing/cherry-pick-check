# cherry-pick-check

A CLI tool to check if GitHub PRs have been cherry-picked to release branches.

## Features

- Query PRs by a specific user in a repository
- Auto-detect release branches (e.g., `2.5`, `2.6`)
- Detect cherry-pick status for each target branch
- Display results in a formatted table with clickable links
- Support GitHub CLI and environment variable authentication

## Installation

### Install from PyPI (Recommended)

```bash
pip install cherry-pick-check
```

### Install from Source

```bash
# Clone the repository
git clone https://github.com/zhuwenxing/cherry-pick-check.git
cd cherry-pick-check

# Install with pip
pip install .

# Or install with uv
uv pip install .
```

### Requirements

- Python 3.10+

## Authentication

Configure GitHub authentication using one of the following methods:

### Method 1: GitHub CLI (Recommended)

```bash
# Install GitHub CLI
# macOS
brew install gh

# Ubuntu
sudo apt install gh

# Login
gh auth login
```

### Method 2: Environment Variable

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo` (private repos) or `public_repo` (public repos)
4. Set the environment variable:

```bash
export GITHUB_TOKEN=your_token_here
```

## Usage

### Basic Usage

```bash
# Check user's PRs from the last 30 days
cherry-pick-check <username>
```

### Common Options

```bash
# Specify repository and source branch
cherry-pick-check zhuwenxing -r milvus-io/milvus -b master

# Specify target branches (can be used multiple times)
cherry-pick-check zhuwenxing -t 2.6

# Specify start date
cherry-pick-check zhuwenxing -t 2.6 --since 2025-10-01

# Include all release branches (including patch versions like 2.6.1)
cherry-pick-check zhuwenxing --all-branches

# Show verbose output
cherry-pick-check zhuwenxing -v
```

### Full Options Reference

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `USERNAME` | - | GitHub username (required) | - |
| `--repo` | `-r` | Repository in `owner/repo` format | `milvus-io/milvus` |
| `--branch` | `-b` | Source branch | `master` |
| `--target` | `-t` | Target branch (can specify multiple) | Auto-detect |
| `--since` | - | Start date in `YYYY-MM-DD` format | 30 days ago |
| `--all-branches` | - | Include all release branches | No |
| `--verbose` | `-v` | Show verbose output | No |
| `--version` | - | Show version | - |

## Output

The tool displays a table with the following columns:

| Column | Description |
|--------|-------------|
| PR # | PR number (clickable link) |
| Title | PR title |
| Status | PR state: `open` (yellow) / `merged` (green) |
| Created | Creation date |
| Merged | Merge date |
| 2.6, 2.5... | Cherry-pick status for each target branch |

Cherry-pick status indicators:
- `#45453` (green) - Merged cherry-pick PR
- `#45800 (open)` (yellow) - Open cherry-pick PR
- `x` (red) - Not cherry-picked

## Example Output

```bash
$ cherry-pick-check zhuwenxing -t 2.6 --since 2025-10-01
```

```
Repo: milvus-io/milvus
User: zhuwenxing
Branch: master
Since: 2025-10-01
Found: 14 PRs (1 open, 13 merged)

                               Cherry-Pick Status
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ PR #   ┃ Title                   ┃ Status ┃ Created ┃ Merged ┃      2.6      ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ #45624 │ test: add cdc e2e       │  open  │  11-17  │   -    │       x       │
│        │ testcases               │        │         │        │               │
├────────┼─────────────────────────┼────────┼─────────┼────────┼───────────────┤
│ #45901 │ test: refactor          │ merged │  11-27  │ 11-27  │       x       │
│        │ connection method...    │        │         │        │               │
├────────┼─────────────────────────┼────────┼─────────┼────────┼───────────────┤
│ #45524 │ test: refactor checker  │ merged │  11-12  │ 11-20  │ #45800 (open) │
│        │ to using ...            │        │         │        │               │
├────────┼─────────────────────────┼────────┼─────────┼────────┼───────────────┤
│ #45309 │ test:  add struct array │ merged │  11-05  │ 11-10  │    #45453     │
│        │ mmap tes...             │        │         │        │               │
├────────┼─────────────────────────┼────────┼─────────┼────────┼───────────────┤
│ #45189 │ test: add json dumps    │ merged │  10-31  │ 11-03  │    #45219     │
│        │ for json st...          │        │         │        │               │
├────────┼─────────────────────────┼────────┼─────────┼────────┼───────────────┤
│ #44940 │ test: add struct array  │ merged │  10-17  │ 10-20  │    #44973     │
│        │ testcases               │        │         │        │               │
└────────┴─────────────────────────┴────────┴─────────┴────────┴───────────────┘

Summary: 14 PRs (1 open, 13 merged) across 1 branches
  Cherry-picked: 5 merged, 3 open, 6 not picked
```

## How Detection Works

The tool searches for PRs that reference the source PR in their body. Supported formats:

- `Cherry-pick from master\npr: #45309`
- `pr: https://github.com/milvus-io/milvus/pull/45309`
- `backport #45309`
- `also pick pr: #45309`

This is compatible with the milvus-io/milvus cherry-pick workflow.

## FAQ

### 1. Authentication Error

Make sure you have configured GitHub authentication. See [Authentication](#authentication).

### 2. Rate Limit Error

GitHub API has rate limits. The tool will auto-wait (up to 2 minutes), or you can retry later.

### 3. No Release Branches Detected

If your repository doesn't use standard version naming (e.g., `2.5`, `2.6`), use `-t` to manually specify target branches.

### 4. Cherry-pick PR Not Detected

Make sure the cherry-pick PR body contains a reference to the source PR. See [How Detection Works](#how-detection-works).

## License

MIT

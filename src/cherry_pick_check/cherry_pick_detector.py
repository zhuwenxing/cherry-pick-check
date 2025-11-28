from datetime import datetime

from rich.progress import Progress, SpinnerColumn, TextColumn

from .github_client import GitHubClient
from .models import CherryPickResult, CherryPickStatus, PRInfo, PRState

# Keywords that indicate a cherry-pick PR
CHERRY_PICK_KEYWORDS = [
    "cherry-pick",
    "cherry pick",
    "cherrypick",
    "backport",
    "pick pr",
]


def _is_cherry_pick_reference(body: str, source_pr_number: int, repo: str = "") -> bool:
    """Check if PR body indicates a cherry-pick of the source PR.

    Supports various formats used in milvus-io/milvus:
    - "Cherry-pick from master\\npr: #45911"
    - "pr: https://github.com/milvus-io/milvus/pull/45111"
    - "also pick pr: #45237"

    Args:
        body: PR body text.
        source_pr_number: The source PR number to check for.
        repo: Repository in format 'owner/repo' for URL matching.

    Returns:
        True if the body indicates this is a cherry-pick of the source PR.
    """
    if not body:
        return False

    body_lower = body.lower()

    # Check for cherry-pick keywords
    has_keyword = any(kw in body_lower for kw in CHERRY_PICK_KEYWORDS)

    # Check for reference to the source PR in various formats
    pr_patterns = [
        f"#{source_pr_number}",  # #12345
        f"pull/{source_pr_number}",  # URL pattern: /pull/12345
        f"pr: #{source_pr_number}",
        f"pr: {source_pr_number}",
        f"pr:#{source_pr_number}",
        f"pr:{source_pr_number}",
    ]

    has_reference = any(pattern in body or pattern in body_lower for pattern in pr_patterns)

    # For milvus style: if body has "pr:" prefix with PR reference, treat as cherry-pick
    # even without explicit cherry-pick keywords
    has_pr_prefix = "pr:" in body_lower or "pr :" in body_lower
    if has_pr_prefix and has_reference:
        return True

    return has_keyword and has_reference


def _parse_pr_state(pr_data: dict) -> PRState:
    """Parse PR state from API data.

    Args:
        pr_data: Raw PR data from GitHub API.

    Returns:
        PRState enum value.
    """
    # Check if merged
    merged_at = pr_data.get("pull_request", {}).get("merged_at") or pr_data.get("merged_at")
    if merged_at:
        return PRState.MERGED

    # Check state field
    state = pr_data.get("state", "").lower()
    if state == "open":
        return PRState.OPEN
    elif state == "closed":
        return PRState.CLOSED

    return PRState.OPEN


def _parse_pr_info(pr_data: dict, base_branch: str | None = None) -> PRInfo:
    """Parse PR data into PRInfo model.

    Args:
        pr_data: Raw PR data from GitHub API.
        base_branch: Override base branch if known.

    Returns:
        PRInfo model instance.
    """
    # Parse created_at
    created_at = None
    if pr_data.get("created_at"):
        created_at = datetime.fromisoformat(
            pr_data["created_at"].replace("Z", "+00:00")
        )

    # Parse merged_at
    merged_at = None
    if pr_data.get("pull_request", {}).get("merged_at"):
        merged_at = datetime.fromisoformat(
            pr_data["pull_request"]["merged_at"].replace("Z", "+00:00")
        )
    elif pr_data.get("merged_at"):
        merged_at = datetime.fromisoformat(
            pr_data["merged_at"].replace("Z", "+00:00")
        )

    return PRInfo(
        number=pr_data["number"],
        title=pr_data["title"],
        url=pr_data["html_url"],
        author=pr_data["user"]["login"],
        state=_parse_pr_state(pr_data),
        created_at=created_at,
        merged_at=merged_at,
        base_branch=base_branch or pr_data.get("base", {}).get("ref", "unknown"),
    )


class CherryPickDetector:
    """Detector for finding cherry-pick status of PRs."""

    def __init__(self, client: GitHubClient):
        self.client = client

    def get_user_prs(
        self,
        repo: str,
        author: str,
        base_branch: str,
        since: datetime | None = None,
        include_open: bool = True,
    ) -> list[PRInfo]:
        """Get PRs by a user on a specific branch.

        Args:
            repo: Repository in format 'owner/repo'.
            author: GitHub username.
            base_branch: Target branch name.
            since: Only return PRs created/merged after this date.
            include_open: Include open PRs in addition to merged ones.

        Returns:
            List of PRInfo objects.
        """
        prs = []
        for pr_data in self.client.get_user_prs(repo, author, base_branch, since, include_open):
            prs.append(_parse_pr_info(pr_data, base_branch))
        return prs

    def detect_cherry_picks(
        self,
        repo: str,
        source_prs: list[PRInfo],
        target_branches: list[str],
        show_progress: bool = True,
    ) -> list[CherryPickResult]:
        """Detect cherry-pick status for multiple PRs.

        Args:
            repo: Repository in format 'owner/repo'.
            source_prs: List of source PRs to check.
            target_branches: List of target branches to check.
            show_progress: Whether to show progress bar.

        Returns:
            List of CherryPickResult objects.
        """
        results = []

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task(
                    "Checking cherry-pick status...", total=len(source_prs)
                )

                for pr in source_prs:
                    pr_results = self._detect_for_pr(repo, pr, target_branches)
                    results.extend(pr_results)
                    progress.advance(task)
        else:
            for pr in source_prs:
                pr_results = self._detect_for_pr(repo, pr, target_branches)
                results.extend(pr_results)

        return results

    def _detect_for_pr(
        self,
        repo: str,
        source_pr: PRInfo,
        target_branches: list[str],
    ) -> list[CherryPickResult]:
        """Detect cherry-pick status for a single PR.

        Args:
            repo: Repository in format 'owner/repo'.
            source_pr: Source PR to check.
            target_branches: List of target branches to check.

        Returns:
            List of CherryPickResult objects for each target branch.
        """
        # Search for PRs that reference this PR
        related_prs = self.client.search_related_prs(repo, source_pr.number)

        # Build a map of target branch -> related cherry-pick PR
        branch_to_cp: dict[str, PRInfo] = {}

        for pr_data in related_prs:
            # Skip if it's the same PR
            if pr_data["number"] == source_pr.number:
                continue

            # Check if body indicates cherry-pick
            body = pr_data.get("body", "") or ""
            if not _is_cherry_pick_reference(body, source_pr.number):
                continue

            # Get PR details to find target branch
            try:
                pr_detail = self.client.get_pr_details(repo, pr_data["number"])
                target_branch = pr_detail["base"]["ref"]

                if target_branch in target_branches:
                    branch_to_cp[target_branch] = _parse_pr_info(pr_detail, target_branch)
            except Exception:
                # Skip if we can't get PR details
                continue

        # Build results for all target branches
        results = []
        for branch in target_branches:
            if branch in branch_to_cp:
                results.append(
                    CherryPickResult(
                        source_pr=source_pr,
                        target_branch=branch,
                        status=CherryPickStatus.PICKED,
                        related_pr=branch_to_cp[branch],
                        detection_method="PR body reference",
                    )
                )
            else:
                results.append(
                    CherryPickResult(
                        source_pr=source_pr,
                        target_branch=branch,
                        status=CherryPickStatus.NOT_PICKED,
                    )
                )

        return results

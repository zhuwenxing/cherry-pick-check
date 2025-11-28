import re
from functools import cmp_to_key

# Release branch patterns for milvus-io/milvus and similar projects
RELEASE_BRANCH_PATTERNS = [
    r"^\d+\.\d+$",  # e.g., 2.4, 2.5
    r"^\d+\.\d+\.\d+$",  # e.g., 2.0.2, 2.2.5
    r"^\d+\.x$",  # e.g., 2.x
    r"^\d+\.\d+\.x$",  # e.g., 2.4.x
]


def _parse_version(branch: str) -> tuple[int, ...]:
    """Parse version numbers from branch name.

    Args:
        branch: Branch name like '2.4' or '2.4.x'.

    Returns:
        Tuple of version numbers.
    """
    # Remove trailing .x if present
    clean = branch.rstrip(".x")
    parts = clean.split(".")
    return tuple(int(p) for p in parts if p.isdigit())


def _version_compare(a: str, b: str) -> int:
    """Compare two version strings.

    Args:
        a: First version string.
        b: Second version string.

    Returns:
        Negative if a < b, positive if a > b, zero if equal.
    """
    va = _parse_version(a)
    vb = _parse_version(b)

    # Compare component by component
    for i in range(max(len(va), len(vb))):
        na = va[i] if i < len(va) else 0
        nb = vb[i] if i < len(vb) else 0
        if na != nb:
            return na - nb
    return 0


def detect_release_branches(
    all_branches: list[str],
    exclude_branch: str | None = None,
    major_only: bool = True,
    limit: int | None = None,
) -> list[str]:
    """Detect release branches from a list of branch names.

    Args:
        all_branches: List of all branch names.
        exclude_branch: Branch to exclude (usually the source branch).
        major_only: If True, only include major version branches (e.g., 2.4, 2.5).
        limit: Maximum number of branches to return.

    Returns:
        List of release branch names, sorted by version (newest first).
    """
    # Pattern for major versions only (e.g., 2.4, 2.5, not 2.4.1)
    major_pattern = r"^\d+\.\d+$"
    combined_pattern = "|".join(f"({p})" for p in RELEASE_BRANCH_PATTERNS)

    release_branches = []

    for branch in all_branches:
        if branch == exclude_branch:
            continue

        if major_only:
            if re.match(major_pattern, branch):
                release_branches.append(branch)
        else:
            if re.match(combined_pattern, branch):
                release_branches.append(branch)

    # Sort by version, newest first
    sorted_branches = sorted(release_branches, key=cmp_to_key(_version_compare), reverse=True)

    if limit:
        return sorted_branches[:limit]
    return sorted_branches


def filter_branches(
    all_branches: list[str],
    target_branches: list[str],
) -> list[str]:
    """Filter branches to only include those that exist.

    Args:
        all_branches: List of all branch names in the repository.
        target_branches: List of target branch names to filter.

    Returns:
        List of target branches that exist in the repository.
    """
    all_set = set(all_branches)
    return [b for b in target_branches if b in all_set]

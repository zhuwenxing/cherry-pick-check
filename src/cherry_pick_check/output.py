from rich.console import Console
from rich.table import Table

from .models import CherryPickResult, CherryPickStatus, PRState


def _format_pr_state(state: PRState) -> str:
    """Format PR state with color.

    Args:
        state: PR state enum.

    Returns:
        Formatted state string with color.
    """
    if state == PRState.OPEN:
        return "[yellow]open[/yellow]"
    elif state == PRState.MERGED:
        return "[green]merged[/green]"
    else:
        return "[dim]closed[/dim]"


def _format_cp_cell(result: CherryPickResult | None) -> str:
    """Format cherry-pick cell with PR number and state.

    Args:
        result: CherryPickResult or None.

    Returns:
        Formatted cell string.
    """
    if not result:
        return "[red]x[/red]"

    if result.status == CherryPickStatus.PICKED and result.related_pr:
        pr = result.related_pr
        num = pr.number
        url = pr.url

        if pr.state == PRState.OPEN:
            return f"[yellow][link={url}]#{num}[/link] (open)[/yellow]"
        elif pr.state == PRState.MERGED:
            return f"[green][link={url}]#{num}[/link][/green]"
        else:
            return f"[dim][link={url}]#{num}[/link] (closed)[/dim]"

    elif result.status == CherryPickStatus.UNKNOWN:
        return "[yellow]?[/yellow]"

    return "[red]x[/red]"


def print_results_table(
    results: list[CherryPickResult],
    console: Console | None = None,
) -> None:
    """Print cherry-pick detection results as a formatted table.

    Args:
        results: List of CherryPickResult objects.
        console: Rich console instance. If None, a new one is created.
    """
    if console is None:
        console = Console()

    if not results:
        console.print("[yellow]No PRs found.[/yellow]")
        return

    # Group results by source PR
    grouped: dict[int, dict] = {}
    all_branches: set[str] = set()

    for result in results:
        pr_num = result.source_pr.number
        if pr_num not in grouped:
            grouped[pr_num] = {
                "pr": result.source_pr,
                "branches": {},
            }
        grouped[pr_num]["branches"][result.target_branch] = result
        all_branches.add(result.target_branch)

    # Sort branches by version
    sorted_branches = sorted(all_branches, reverse=True)

    # Create table
    table = Table(title="Cherry-Pick Status", show_lines=True)
    table.add_column("PR #", style="cyan", no_wrap=True)
    table.add_column("Title", max_width=35)
    table.add_column("Status", justify="center")
    table.add_column("Created", style="dim", justify="center")
    table.add_column("Merged", style="dim", justify="center")

    for branch in sorted_branches:
        table.add_column(branch, justify="center")

    # Add rows - sort by state (open first) then by PR number
    sorted_prs = sorted(
        grouped.items(),
        key=lambda x: (0 if x[1]["pr"].state == PRState.OPEN else 1, -x[0]),
    )

    for pr_num, data in sorted_prs:
        pr = data["pr"]

        # Format PR number with link
        pr_cell = f"[link={pr.url}]#{pr_num}[/link]"

        # Format status
        status_cell = _format_pr_state(pr.state)

        # Format dates
        created_str = pr.created_at.strftime("%m-%d") if pr.created_at else "-"
        merged_str = pr.merged_at.strftime("%m-%d") if pr.merged_at else "-"

        row = [
            pr_cell,
            _truncate(pr.title, 35),
            status_cell,
            created_str,
            merged_str,
        ]

        for branch in sorted_branches:
            result = data["branches"].get(branch)
            row.append(_format_cp_cell(result))

        table.add_row(*row)

    console.print(table)

    # Print summary
    total_prs = len(grouped)
    open_prs = sum(1 for d in grouped.values() if d["pr"].state == PRState.OPEN)
    merged_prs = total_prs - open_prs

    picked_count = sum(1 for r in results if r.status == CherryPickStatus.PICKED)
    picked_merged = sum(
        1
        for r in results
        if r.status == CherryPickStatus.PICKED
        and r.related_pr
        and r.related_pr.state == PRState.MERGED
    )
    picked_open = picked_count - picked_merged

    console.print()
    branch_count = len(sorted_branches)
    pr_stats = f"{total_prs} PRs ({open_prs} open, {merged_prs} merged)"
    console.print(f"[bold]Summary:[/bold] {pr_stats} across {branch_count} branches")
    console.print(
        f"  Cherry-picked: [green]{picked_merged} merged[/green], "
        f"[yellow]{picked_open} open[/yellow], "
        f"[red]{len(results) - picked_count} not picked[/red]"
    )


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if too long.

    Args:
        text: Text to truncate.
        max_len: Maximum length.

    Returns:
        Truncated text.
    """
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."

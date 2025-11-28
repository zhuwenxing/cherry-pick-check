from datetime import datetime, timedelta

import click
from rich.console import Console

from .auth import AuthenticationError, get_github_token
from .branch_detector import detect_release_branches, filter_branches
from .cherry_pick_detector import CherryPickDetector
from .github_client import GitHubClient, RateLimitError
from .output import print_results_table


@click.command()
@click.argument("username")
@click.option(
    "-r",
    "--repo",
    default="milvus-io/milvus",
    help="GitHub repository in format 'owner/repo'.",
)
@click.option(
    "-b",
    "--branch",
    default="master",
    help="Source branch to check PRs from.",
)
@click.option(
    "-t",
    "--target",
    multiple=True,
    help="Target branch to check (can be specified multiple times). "
    "If not specified, auto-detects release branches.",
)
@click.option(
    "--since",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str((datetime.now() - timedelta(days=30)).date()),
    help="Only check PRs merged after this date (YYYY-MM-DD). Default: 30 days ago.",
)
@click.option(
    "--all-branches",
    is_flag=True,
    help="Include all release branches (including patch versions like 2.4.1).",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show verbose output.",
)
@click.version_option(version="0.1.0")
def cli(
    username: str,
    repo: str,
    branch: str,
    target: tuple[str, ...],
    since: datetime,
    all_branches: bool,
    verbose: bool,
) -> None:
    """Check if a user's PRs have been cherry-picked to release branches.

    USERNAME is the GitHub username to check PRs for.

    Examples:

        cherry-pick-check zhuwenxing

        cherry-pick-check zhuwenxing -r milvus-io/milvus -b master

        cherry-pick-check zhuwenxing -t 2.4 -t 2.5
    """
    console = Console()

    # Get authentication
    try:
        token = get_github_token()
    except AuthenticationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)

    if verbose:
        console.print("[dim]Authenticated with GitHub[/dim]")

    try:
        with GitHubClient(token) as client:
            detector = CherryPickDetector(client)

            # Get user's PRs
            if verbose:
                msg = f"Fetching PRs by {username} on {repo}:{branch} since {since.date()}..."
                console.print(f"[dim]{msg}[/dim]")

            source_prs = detector.get_user_prs(repo, username, branch, since)

            if not source_prs:
                msg = f"No PRs found for {username} on {repo}:{branch} since {since.date()}"
                console.print(f"[yellow]{msg}[/yellow]")
                return

            # Print query info
            console.print(f"[bold]Repo:[/bold] {repo}")
            console.print(f"[bold]User:[/bold] {username}")
            console.print(f"[bold]Branch:[/bold] {branch}")
            console.print(f"[bold]Since:[/bold] {since.date()}")

            # Count open and merged PRs
            from .models import PRState

            open_count = sum(1 for pr in source_prs if pr.state == PRState.OPEN)
            merged_count = len(source_prs) - open_count
            console.print(
                f"[bold]Found:[/bold] {len(source_prs)} PRs "
                f"([yellow]{open_count} open[/yellow], [green]{merged_count} merged[/green])"
            )

            # Determine target branches
            if target:
                # User specified target branches
                all_branches = client.get_branches(repo)
                target_branches = filter_branches(all_branches, list(target))
                if not target_branches:
                    msg = f"None of the specified branches exist: {', '.join(target)}"
                    console.print(f"[red]Error:[/red] {msg}")
                    raise SystemExit(1)
            else:
                # Auto-detect release branches
                if verbose:
                    console.print("[dim]Auto-detecting release branches...[/dim]")
                repo_branches = client.get_branches(repo)
                target_branches = detect_release_branches(
                    repo_branches,
                    exclude_branch=branch,
                    major_only=not all_branches,
                )
                if not target_branches:
                    msg = "No release branches detected. Use -t to specify target branches."
                    console.print(f"[yellow]{msg}[/yellow]")
                    return

            if verbose:
                console.print(f"[dim]Target branches: {', '.join(target_branches)}[/dim]")

            # Detect cherry-picks
            results = detector.detect_cherry_picks(
                repo, source_prs, target_branches, show_progress=True
            )

            # Print results
            console.print()
            print_results_table(results, console)

    except RateLimitError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise SystemExit(1)

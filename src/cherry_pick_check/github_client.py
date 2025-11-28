import time
from datetime import datetime
from typing import Generator

import httpx
from rich.console import Console


class RateLimitError(Exception):
    """Raised when GitHub API rate limit is exceeded."""

    pass


class GitHubClient:
    """GitHub API client with pagination and rate limit handling."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str, auto_wait: bool = True):
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        self.auto_wait = auto_wait
        self.console = Console()

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_user_prs(
        self,
        repo: str,
        author: str,
        base_branch: str,
        since: datetime | None = None,
        include_open: bool = True,
    ) -> Generator[dict, None, None]:
        """Get PRs by a user on a specific branch.

        Args:
            repo: Repository in format 'owner/repo'.
            author: GitHub username.
            base_branch: Target branch name.
            since: Only return PRs created/merged after this date.
            include_open: Include open PRs in addition to merged ones.

        Yields:
            PR data dictionaries.
        """
        # Get merged PRs
        query = f"repo:{repo} is:pr is:merged author:{author} base:{base_branch}"
        if since:
            query += f" merged:>={since.strftime('%Y-%m-%d')}"
        yield from self._search_issues(query)

        # Get open PRs
        if include_open:
            query = f"repo:{repo} is:pr is:open author:{author} base:{base_branch}"
            if since:
                query += f" created:>={since.strftime('%Y-%m-%d')}"
            yield from self._search_issues(query)

    def search_related_prs(self, repo: str, pr_number: int) -> list[dict]:
        """Search for PRs that reference a specific PR number.

        Args:
            repo: Repository in format 'owner/repo'.
            pr_number: The PR number to search for references.

        Returns:
            List of PR data dictionaries.
        """
        # Search all PRs (open + merged + closed) that reference this PR
        query = f"repo:{repo} is:pr {pr_number} in:body"
        return list(self._search_issues(query))

    def get_pr_details(self, repo: str, pr_number: int) -> dict:
        """Get detailed information about a specific PR.

        Args:
            repo: Repository in format 'owner/repo'.
            pr_number: The PR number.

        Returns:
            PR details dictionary.
        """
        while True:
            response = self.client.get(f"/repos/{repo}/pulls/{pr_number}")
            if self._handle_rate_limit(response):
                continue  # Retry after waiting
            response.raise_for_status()
            return response.json()

    def get_branches(self, repo: str) -> list[str]:
        """Get all branch names in a repository.

        Args:
            repo: Repository in format 'owner/repo'.

        Returns:
            List of branch names.
        """
        branches = []
        for branch in self._paginate(f"/repos/{repo}/branches"):
            branches.append(branch["name"])
        return branches

    def _search_issues(self, query: str) -> Generator[dict, None, None]:
        """Search issues/PRs using GitHub Search API.

        Args:
            query: Search query string.

        Yields:
            Issue/PR data dictionaries.
        """
        params = {"q": query, "per_page": 100}
        page = 1

        while True:
            params["page"] = page
            response = self.client.get("/search/issues", params=params)
            if self._handle_rate_limit(response):
                continue  # Retry after waiting
            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])

            if not items:
                break

            yield from items

            # Check if there are more pages
            if len(items) < 100:
                break

            page += 1

    def _paginate(
        self, endpoint: str, params: dict | None = None
    ) -> Generator[dict, None, None]:
        """Handle paginated API requests.

        Args:
            endpoint: API endpoint path.
            params: Optional query parameters.

        Yields:
            Response items.
        """
        params = params or {}
        params["per_page"] = 100
        page = 1

        while True:
            params["page"] = page
            response = self.client.get(endpoint, params=params)
            if self._handle_rate_limit(response):
                continue  # Retry after waiting
            response.raise_for_status()

            data = response.json()

            if not data:
                break

            yield from data

            if len(data) < 100:
                break

            page += 1

    def _handle_rate_limit(self, response: httpx.Response) -> bool:
        """Check and handle rate limit from response headers.

        Args:
            response: HTTP response object.

        Returns:
            True if request should be retried after waiting.

        Raises:
            RateLimitError: If rate limit is exceeded and auto_wait is disabled.
        """
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset_timestamp = response.headers.get("X-RateLimit-Reset")

        if remaining is not None and int(remaining) == 0:
            if reset_timestamp:
                reset_time = int(reset_timestamp)
                wait_seconds = max(0, reset_time - int(time.time())) + 1

                if self.auto_wait and wait_seconds <= 120:  # Max wait 2 minutes
                    self.console.print(
                        f"[yellow]Rate limit reached. Waiting {wait_seconds} seconds...[/yellow]"
                    )
                    time.sleep(wait_seconds)
                    return True  # Signal to retry
                else:
                    reset_dt = datetime.fromtimestamp(reset_time)
                    raise RateLimitError(
                        f"GitHub API rate limit exceeded. Resets at: {reset_dt.strftime('%H:%M:%S')}\n"
                        f"Try again in {wait_seconds} seconds, or wait and re-run the command."
                    )
            else:
                raise RateLimitError("GitHub API rate limit exceeded.")

        # Proactively slow down if remaining is low
        if remaining is not None and int(remaining) < 5:
            time.sleep(2)  # Slow down to avoid hitting limit

        return False

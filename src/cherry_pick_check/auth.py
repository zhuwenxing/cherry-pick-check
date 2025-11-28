import os
import subprocess


class AuthenticationError(Exception):
    """Raised when GitHub authentication fails."""

    pass


def get_github_token() -> str:
    """Get GitHub token from gh CLI or environment variable.

    Returns:
        GitHub authentication token.

    Raises:
        AuthenticationError: If no token can be obtained.
    """
    # 1. Try gh CLI first (usually has better token management)
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
        token = result.stdout.strip()
        if token:
            return token
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # 2. Fallback to environment variable
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    raise AuthenticationError(
        "Cannot obtain GitHub authentication.\n\n"
        "Please configure authentication using one of the following methods:\n\n"
        "Method 1: Set GITHUB_TOKEN environment variable\n"
        "  1. Go to https://github.com/settings/tokens\n"
        "  2. Click 'Generate new token (classic)'\n"
        "  3. Select scopes: 'repo' (for private repos) or 'public_repo' (for public repos)\n"
        "  4. Copy the token and set it:\n"
        "     export GITHUB_TOKEN=your_token_here\n\n"
        "Method 2: Use GitHub CLI (gh)\n"
        "  1. Install gh: https://cli.github.com/\n"
        "     - macOS: brew install gh\n"
        "     - Ubuntu: sudo apt install gh\n"
        "  2. Login: gh auth login"
    )

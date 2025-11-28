"""Tests for models module."""

from datetime import datetime

from cherry_pick_check.models import (
    CherryPickResult,
    CherryPickStatus,
    PRInfo,
    PRState,
)


def test_pr_info_creation():
    """Test PRInfo model creation."""
    pr = PRInfo(
        number=123,
        title="Test PR",
        url="https://github.com/owner/repo/pull/123",
        author="testuser",
        state=PRState.MERGED,
        created_at=datetime(2024, 1, 1),
        merged_at=datetime(2024, 1, 2),
        base_branch="main",
    )
    assert pr.number == 123
    assert pr.state == PRState.MERGED
    assert pr.merged_at is not None


def test_cherry_pick_result():
    """Test CherryPickResult model."""
    source_pr = PRInfo(
        number=123,
        title="Source PR",
        url="https://github.com/owner/repo/pull/123",
        author="testuser",
        state=PRState.MERGED,
        created_at=None,
        merged_at=None,
        base_branch="main",
    )
    result = CherryPickResult(
        source_pr=source_pr,
        target_branch="2.4",
        status=CherryPickStatus.PICKED,
        related_pr=None,
        detection_method="pattern_match",
    )
    assert result.status == CherryPickStatus.PICKED
    assert result.target_branch == "2.4"

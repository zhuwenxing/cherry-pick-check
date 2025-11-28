"""Tests for branch_detector module."""

from cherry_pick_check.branch_detector import (
    detect_release_branches,
    filter_branches,
)


def test_detect_release_branches_basic():
    """Test basic release branch detection."""
    branches = ["main", "2.4", "2.5", "2.3", "feature-x"]
    result = detect_release_branches(branches, exclude=["main"])
    assert "2.5" in result
    assert "2.4" in result
    assert "2.3" in result
    assert "main" not in result
    assert "feature-x" not in result


def test_detect_release_branches_with_x_suffix():
    """Test detection of branches with .x suffix."""
    branches = ["main", "2.4.x", "2.5.x", "dev"]
    result = detect_release_branches(branches, exclude=["main"])
    assert "2.4.x" in result
    assert "2.5.x" in result


def test_filter_branches():
    """Test filtering branches by target list."""
    all_branches = ["main", "2.4", "2.5", "2.3"]
    targets = ["2.4", "2.5"]
    result = filter_branches(all_branches, targets)
    assert result == ["2.4", "2.5"]


def test_filter_branches_missing():
    """Test filtering with non-existent branch."""
    all_branches = ["main", "2.4", "2.5"]
    targets = ["2.4", "2.6"]
    result = filter_branches(all_branches, targets)
    assert result == ["2.4"]

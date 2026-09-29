from eks_upgrade_advisor.chart_compat import ArtifactHubClient
from eks_upgrade_advisor.models import CompatStatus


def test_resolve_status_no_constraint_is_unknown() -> None:
    assert ArtifactHubClient._resolve_status(None, "1.30") == CompatStatus.UNKNOWN


def test_resolve_status_simple_gte_compatible() -> None:
    assert ArtifactHubClient._resolve_status(">=1.28.0-0", "1.30") == CompatStatus.COMPATIBLE


def test_resolve_status_simple_gte_upgrade_required() -> None:
    assert ArtifactHubClient._resolve_status(">=1.31.0", "1.30") == CompatStatus.UPGRADE_REQUIRED


def test_resolve_status_and_range_within_bounds() -> None:
    assert ArtifactHubClient._resolve_status(">=1.28.0-0,<1.31.0", "1.30") == CompatStatus.COMPATIBLE


def test_resolve_status_and_range_outside_upper_bound() -> None:
    assert ArtifactHubClient._resolve_status(">=1.28.0-0,<1.30.0", "1.30") == CompatStatus.UPGRADE_REQUIRED


def test_resolve_status_or_groups() -> None:
    # Matches the second OR group.
    assert ArtifactHubClient._resolve_status("<1.25.0 || >=1.29.0", "1.30") == CompatStatus.COMPATIBLE


def test_resolve_status_or_groups_no_match() -> None:
    assert ArtifactHubClient._resolve_status("<1.25.0 || >=1.35.0", "1.30") == CompatStatus.UPGRADE_REQUIRED


def test_resolve_status_unparseable_constraint_is_unknown() -> None:
    assert ArtifactHubClient._resolve_status("~1.30.x", "1.30") == CompatStatus.UNKNOWN


def test_resolve_status_target_without_patch_normalizes() -> None:
    assert ArtifactHubClient._resolve_status(">=1.30.0", "1.30") == CompatStatus.COMPATIBLE

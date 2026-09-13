import pytest

from app.security.rbac import Principal, authorize_roles


def test_collector_cannot_read_protected_source_identity():
    principal = Principal(subject="collector-1", roles={"draco_collector"})
    with pytest.raises(PermissionError):
        authorize_roles(principal, {"draco_source_admin", "draco_admin"})


def test_source_admin_can_read_protected_source_identity():
    principal = Principal(subject="source-admin-1", roles={"draco_source_admin"})
    authorize_roles(principal, {"draco_source_admin", "draco_admin"})


def test_analyst_cannot_administer_protected_sources():
    principal = Principal(subject="analyst-1", roles={"draco_analyst"})
    with pytest.raises(PermissionError):
        authorize_roles(principal, {"draco_source_admin", "draco_admin"})

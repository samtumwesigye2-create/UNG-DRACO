from fastapi.testclient import TestClient

from app.database import engine
from app.main import app
from app.models import Base
from app.security.auth import get_current_principal
from app.security.rbac import Principal


OPERATIONAL_PATHS = [
    "/api/draco/v1/observations",
    "/api/draco/v1/tracks",
    "/api/draco/v1/alerts",
    "/api/draco/v1/products",
    "/api/draco/v1/audit",
]


def test_operational_reads_require_identity_and_allow_analyst():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    for path in OPERATIONAL_PATHS:
        assert client.get(path).status_code == 401

    app.dependency_overrides[get_current_principal] = lambda: Principal(
        subject="analyst-operations", roles={"draco_analyst"}
    )
    try:
        for path in OPERATIONAL_PATHS:
            response = client.get(path)
            assert response.status_code == 200
            assert isinstance(response.json(), list)
    finally:
        app.dependency_overrides.clear()

from fastapi import Depends, FastAPI, Response, status

from app.database import database_ready
from app.security.auth import get_current_principal
from app.security.rbac import Principal

app = FastAPI(title="UNG-DRACO", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"system": "UNG-DRACO", "status": "ok"}


@app.get("/ready")
def ready(response: Response) -> dict[str, str]:
    if database_ready():
        return {"system": "UNG-DRACO", "status": "ready"}

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"system": "UNG-DRACO", "status": "not_ready"}


@app.get("/v1/security/probe")
def security_probe(principal: Principal = Depends(get_current_principal)) -> dict[str, str]:
    return {"subject": principal.subject, "status": "authenticated"}

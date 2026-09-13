from fastapi import FastAPI, Response, status

from app.database import database_ready

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

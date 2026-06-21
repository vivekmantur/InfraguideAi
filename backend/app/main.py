from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.settings import get_cors_origins
from .routers.assessments import router as assessments_router
from .routers.cloud_intelligence import router as cloud_intelligence_router

app = FastAPI(title="InfraGuide AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assessments_router)
app.include_router(cloud_intelligence_router)

@app.get("/health")
def health() -> dict[str, str]:
    """Return API health status.

    Returns:
        A small dictionary indicating that the API is reachable.
    """
    return {"status": "ok"}

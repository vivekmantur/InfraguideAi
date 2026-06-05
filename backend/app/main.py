from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .analyzer import analyze_repository
from .models import AssessmentRequest, BlueprintRequest
from .recommendation import build_assessment, render_blueprint

app = FastAPI(title="InfraGuide AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/assessments")
def create_assessment(request: AssessmentRequest):
    analysis, warnings = analyze_repository(str(request.repository_url))
    return build_assessment(request, analysis, warnings)


@app.post("/api/assessments/blueprint", response_class=PlainTextResponse)
def export_blueprint(request: BlueprintRequest):
    return render_blueprint(request.assessment)

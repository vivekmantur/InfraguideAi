# InfraGuide AI

AI-powered cloud migration intelligence platform for generating repository assessments, cloud readiness scores, service recommendations, migration strategies, roadmaps, and migration blueprints.

## MVP Features

- GitHub repository URL input
- Migration requirements form
- Repository analysis for languages, frameworks, databases, package managers, and containers
- Cloud readiness scoring
- Cloud provider and service recommendations
- Migration strategy and roadmap generation
- Markdown blueprint export

## Tech Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS
- Backend: FastAPI
- Repository analysis: GitPython plus custom analyzers
- AI-ready layer: deterministic MVP logic now, OpenAI/Azure OpenAI hook later

## Run Locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## API

- `POST /api/assessments` generates the migration assessment.
- `POST /api/assessments/blueprint` returns a Markdown migration blueprint.

## Notes

This MVP does not perform cloud provisioning, infrastructure scanning, or real migration execution. It focuses on the planning workflow for hackathon scope.

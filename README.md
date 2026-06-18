# InfraGuide AI

AI-powered cloud migration intelligence platform for generating repository assessments, cloud readiness scores, service recommendations, migration strategies, roadmaps, and migration blueprints.

## MVP Features

- GitHub repository URL input
- Local project folder upload
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
uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### MCP Pricing And Cloud Intelligence

```bash
docker start infraguide-redis
cd cloud-intelligence-mcp
python app.py
```

In a second terminal:

```bash
cd cloud-intelligence-mcp
.\.venv\Scripts\mcp-uvicorn.cmd bridge_api:app --host 127.0.0.1 --port 8001
```

## API

- `POST /assessments` generates a migration assessment from a GitHub repository URL.
- `POST /assessments/upload` generates a migration assessment from multipart uploaded folder files.
- `POST /assessments/blueprint` returns a Markdown migration blueprint.
- `POST /pricing/regions` gets Azure/GCP regional pricing through the MCP bridge.
- `GET /cloud-intelligence/health` checks MCP and Redis cache health.
- `POST /cloud-intelligence/service-availability` checks provider service availability for a region.
- `POST /cloud-intelligence/runtime-support` checks runtime support for a target cloud service.
- `POST /cloud-intelligence/service-limits` returns deterministic service limit notes.

Cloud intelligence fallback catalogs live in `cloud-intelligence-mcp/catalogs/*.json`.
These JSON files provide editable local defaults for regions, service aliases, runtime support, and service limit notes.

## Notes

This MVP does not perform cloud provisioning, infrastructure scanning, or real migration execution. It focuses on the planning workflow for hackathon scope.

# Production Deployment

This repo deploys to the Linux server with GitHub Actions.

## What Happens On Push

Every push to `main` runs `.github/workflows/deploy.yml`.

The workflow:

1. Connects to `root@62.72.30.227` over SSH.
2. Goes to `/home/amisha/InfraguideAi`.
3. Pulls the latest `main` code from GitHub.
4. Rebuilds the Docker image with Docker Compose.
5. Restarts the app container with the new image.

## Required GitHub Secret

In GitHub, open:

`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

Add this secret:

```text
DEPLOY_SSH_PASSWORD
```

The value must be the SSH password that can log in to the server as `root`.

## Server Setup

The server should already have:

- Docker installed.
- Docker Compose installed.
- The `root` user can run Docker commands.
- This repo cloned at `/home/amisha/InfraguideAi`.
- A production `.env` file at `/home/amisha/InfraguideAi/.env`.

Use this in the server `.env` so the same code works locally and on the server:

```bash
VITE_API_BASE_URL=
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174,http://62.72.30.227:5174
```

When `VITE_API_BASE_URL` is empty, the frontend automatically calls port `9000` on the same hostname used to open the app. For example, `http://localhost:5173` calls `http://localhost:9000`, and `http://62.72.30.227:5174` calls `http://62.72.30.227:9000`.

Keep your existing cloud and AWS/GCP variables in the same `.env` file.

## Manual Deployment

You can also deploy manually from GitHub:

`Actions` -> `Deploy InfraGuide AI` -> `Run workflow`

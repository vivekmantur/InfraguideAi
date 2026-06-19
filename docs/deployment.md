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

Set this in the server `.env` so the built frontend calls the server API:

```bash
VITE_API_BASE_URL=http://62.72.30.227:9000
CORS_ORIGINS=http://62.72.30.227:5174
```

Keep your existing cloud and AWS/GCP variables in the same `.env` file.

## Manual Deployment

You can also deploy manually from GitHub:

`Actions` -> `Deploy InfraGuide AI` -> `Run workflow`

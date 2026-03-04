# Fly.io MicroVM Setup Guide for Kith Foundry

This guide outlines how to provision the Kith Foundry backend and securely enable the Fly.io Machine REST API for the Agent Bridge sandbox environment.

## 1. Prerequisites
- **Flyctl CLI:** Install the `flyctl` command-line tool.
  ```bash
  # Windows (PowerShell)
  iwr https://fly.io/install.ps1 -useb | iex
  ```
- **Authentication:** Run `fly auth login` to authenticate standard credentials.
- **Docker:** Ensure Docker Desktop is running.

## 2. Generate a Fly API Token
The backend requires a `FLY_API_TOKEN` to communicate with the Fly Machines API to spin up user sandboxes on demand.
1. Generate an API token:
   ```bash
   fly tokens create org -r <your-org-slug>
   # If using a personal account, org is usually "personal"
   # OR for a general token:
   fly tokens create deploy
   ```
2. Copy the resulting token string (`FlY_...`).

## 3. Set Up the Backend Environment Variables
Create a `.env` file in the `kith_foundry/backend` directory containing:

```env
FLY_API_TOKEN=your_token_here
FLY_ORG_SLUG=personal
```

*Note: The FastAPI backend expects these variables to use the `requests` library to orchestrate the VMs.*

## 4. Build and Push the Sandbox Base Image
The Fly Machines API requires a Docker image hosted on a registry to boot from. We will build our custom `Dockerfile.sandbox` and push it to the Fly container registry.

1. **Create an empty Fly App to hold the image:**
   ```bash
   fly apps create kith-sandbox-base
   ```
2. **Build and push the image utilizing the Fly builder:**
   Navigate to the `backend` directory (where `Dockerfile.sandbox` and `bridge.py` live):
   ```bash
   cd backend
   fly deploy --app kith-sandbox-base --dockerfile Dockerfile.sandbox --build-only --push
   ```
   *This command pushes the image to `registry.fly.io/kith-sandbox-base:deployment-xyz`.*

## 5. Update the Orchestrator Service
Since we pushed the base image, we need to ensure the `backend/fly_service.py` knows which image to pull when spinning up a new sandbox machine dynamically.

In `backend/fly_service.py`, inside `create_and_boot_sandbox()`, locate the `machine_config` dict and update the image reference to point to our newly pushed base image:

```json
        "config": {
            "image": "registry.fly.io/kith-sandbox-base:latest", // Update this line
            "guest": {
                "cpu_kind": "shared",
                "cpus": 1,
                "memory_mb": 1024
            },
```

*(Note: Depending on Fly's exact tagging, you might need to find the specific SHA or use `latest` as tagged during push).*

## 6. Understanding the Sandbox Boot Flow
Once configured, the following occurs when a user initiates a chat:
1. `backend/main.py` detects no active sandbox for the session.
2. It calls `create_and_boot_sandbox()`.
3. `fly_service.py` reads `FLY_API_TOKEN`.
4. It hits `https://api.machines.dev/v1/apps` to create a ephemeral app (e.g., `kith-sandbox-abcd123`).
5. It hits `https://api.machines.dev/v1/apps/.../machines` passing the config, pointing to `registry.fly.io/kith-sandbox-base:latest`.
6. The machine boots. Port `3000` is mapped publicly (with `autostart`/`autostop`). Port `9999` is hidden.
7. The machine returns an internal IPv6 address.
8. `fly_service.py` stores the IPv6 address and passes AI-generated edits securely by POSTing to `http://[{ipv6}]:9999/api/v1/edit`.

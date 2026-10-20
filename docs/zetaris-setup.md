# Zetaris setup for TB-CareFlow — Windows/WSL2

**Prepared 20 October 2026, before the official build window.** This is a setup guide, not evidence that our Zetaris account or instance is connected.

Authoritative installation instructions: https://github.com/zetaris/getting-started/blob/main/docs/install/updated_zetaris_installation_guide.md

## Two available routes

**A. Organizer-hosted instance:** HackOS resource text previously said access/details would be released before 22 Oct. If supplied, use the URL/assigned credentials and organization/team namespace; do not start installing your own server unnecessarily. Verify in SQL Editor with `SELECT 1 AS one;`.

**B. Your own local instance:** The updated Zetaris `START-HERE.md` now describes self-hosted Docker or managed AWS. Local can be configured before the build window, provided the portal offers a valid bundle, matching environment file, registry credentials and a suitable licence/evaluation entitlement. The `getting-started` GitHub repo alone is *not* the platform runtime.

## 1. Check Windows prerequisites (PowerShell)

```powershell
wsl --status
docker version
docker compose version
```

- Docker Desktop with WSL2 integration enabled.
- At least **8 GB RAM available to Docker** (preflight fails under 6 GB), **4 CPUs**, **15 GB** free disk space.
- Zetaris platform image is amd64. Registry/network access is required.
- If Docker isn't installed, follow https://docs.docker.com/desktop/ (installation is a change to your machine; do it deliberately).

## 2. Get the Zetaris platform bundle (requires user sign-in)

1. Visit https://cloud.enterprise.zetaris.com/register or sign in to Zetaris Cloud.
2. Open https://cloud.enterprise.zetaris.com/dashboard/download .
3. Download `zetaris-platform.zip`, the **matching** `.env`, and obtain the registry login command/credentials provided in the portal.
4. Check the terms and permitted evaluation/hackathon use. The source repo's Apache license covers recipes, **not** the platform images.
5. Do not upload or commit the archive, `.env`, credentials or licence.

## 3. Install in a WSL2 terminal (after you have the bundle)

```bash
unzip zetaris-platform.zip
cd zetaris-platform
docker version
docker compose version
docker login zetarishackathon.azurecr.io
./preflight.sh
```

Before startup, edit the **platform's supplied** `.env`. Keep its registry/image values unchanged and configure the initial admin email, strong password and organization, plus the documented local settings:
- `ZSPARK_DRIVER_MEM=2g`
- `ZSPARK_DRIVER_CORES=2`
- `ZSPARK_MASTER_URL=local[2]`
- `ZETARIS_API_MAX_HEAP=1g`
- `UI_PORT=3000`
- `ALLOWED_ORIGINS=http://localhost:3000`
- `GUI_URL=http://localhost:3000`
- `COMPOSE_PROFILES` empty/unset
- `ZETARIS_SEED_TPCH=true` if retaining samples

```bash
chmod 600 .env
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps --all
./verify.sh
```

**Expected:** verifier passes 9 checks, essential services healthy and localhost UI works. If the download, matching `.env`, licence or registry credentials are unavailable, STOP and use the organizer-hosted route when available. Do not guess credentials.

## 4. First read-only SQL verification

Open http://localhost:3000 (for local installation), sign in with the administrator you created, open SQL Editor, and run statements **one at a time**:

```sql
SELECT 1 AS one;
SHOW LIGHTNING DATABASES;
```

If samples are available, optionally use:

```sql
SHOW LIGHTNING TABLES NY_TAXI;
SELECT * FROM NY_TAXI.taxi_zones LIMIT 5;
```

The sample tables are optional depending on installation and permissions. An empty result for databases is not a failed connection.

## 5. Prepare the TB-CareFlow Python client (optional, after UI works)

Use the *getting-started* repo's official helpers to avoid inventing endpoint paths:

```bash
git clone https://github.com/zetaris/getting-started.git
cd getting-started
cp .env.example .env.local
```

Edit `.env.local` LOCALLY:

```dotenv
ZETARIS_BASE_URL=http://localhost:3000
ZETARIS_ORG_ID=
ZETARIS_API_KEY=
ZETARIS_QUERY_LIMIT=1000
```

Obtain numeric `ZETARIS_ORG_ID` from **Management → Organisation**, and generate `ZETARIS_API_KEY` from **Management → API Tokens**. Keys are only shown once. Never paste them into chat, GitHub, logs or screenshots.

```bash
python3 scripts/check_zetaris.py
python3 scripts/query_zetaris.py "SELECT 1"
```

These Python helpers call the **UI proxy** using `ZETARIS_BASE_URL` (UI origin); direct REST uses a different `ZETARIS_REST_URL` ending in `/api/v1.0`. Do not confuse them.

Sources:
- https://github.com/zetaris/getting-started/blob/main/START-HERE.md
- https://github.com/zetaris/getting-started/blob/main/docs/connections/client-setup.md
- https://github.com/zetaris/getting-started/blob/main/scripts/HOWTO.md

## Success gate / no-write policy

- [ ] Docker/WSL2 prerequisites pass (local route only).
- [ ] Licensed platform bundle and matching env/registry access obtained (local route only).
- [ ] `./verify.sh` passes (local route only).
- [ ] Login and `SELECT 1 AS one;` succeed.
- [ ] `SHOW LIGHTNING DATABASES;` succeeds.
- [ ] Authorized organization/team namespace identified.
- [ ] Later: first read-only synthetic TB data query succeeds.

**Only after explicit go-ahead** create database sources, tables or datasets (which change the instance). Do not use real TB patient data or official SITB systems.

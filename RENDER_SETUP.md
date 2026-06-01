# ⚠️ Render Setup - One Manual Step Required

The latest commit switched from **Render Native Python** to **Docker runtime**.
Render will not auto-switch your existing service's runtime — you need to do it
manually **one time**.

## Quick steps (2 minutes)

1. Open https://dashboard.render.com/web/YOUR-SERVICE-ID
2. Click **"Settings"** in the left sidebar
3. Scroll down to **"Runtime"** section
4. Change **Runtime** from "Python" to **"Docker"**
5. Set **Dockerfile Path** to: `./Dockerfile`
6. Set **Docker Build Context Directory** to: `.` (root of repo)
7. Click **"Save Changes"** at the bottom
8. Render will auto-redeploy with the Docker build

## What I changed

| File | Change |
|------|--------|
| `Dockerfile` | Self-contained — uses prebuilt wheels (`--only-binary=:all:`), no Rust compile needed |
| `render.yaml` | Docker runtime, root-level context, full env vars |
| `requirements.txt` | Copied to root for Docker build context |

## Why this fixes the build failure

The screenshots show **"metadata-generation-failed"** and **"maturin failed"** —
this is `pydantic-core` trying to compile a Rust extension in Render's read-only
native Python build environment. With Docker we have a real read-write filesystem
and prebuilt wheels install instantly.

## What should work after switch

- ✅ Build completes in ~30 seconds (pip install from wheels)
- ✅ `pydantic-core` installs cleanly (no Rust compile)
- ✅ All deps install (FastAPI, SQLAlchemy, etc.)
- ✅ App starts on `$PORT`
- ✅ `/health` returns 200
- ✅ Admin user auto-seeded on first request

## If build still fails

Check Render logs for the specific error and share it. The most common
follow-up issue is the Docker build context — if Render can't find the
Dockerfile, set **Docker Build Context Directory** to `/` and **Dockerfile
Path** to `Dockerfile`.

## Alternative: Delete and recreate

If you can't find the runtime setting, easiest fix:
1. Delete the current `ai-gateway` web service in Render
2. Go to https://dashboard.render.com/blueprint
3. Connect the same GitHub repo
4. Render will use the new `render.yaml` (Docker runtime)

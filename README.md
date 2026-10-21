# DevSecOps CI/CD Demo

Intentionally vulnerable Flask app used to demo a full DevSecOps pipeline:
secrets scanning, SAST, dependency/image CVE scanning, Dockerfile linting,
Slack alerts, GitOps deploy with ArgoCD, and admission-time policy blocking
with Kyverno.

**Do not deploy this app anywhere public. It is built to be caught by scanners.**

## What's intentionally broken (and why)

| File | Problem | Caught by |
|---|---|---|
| `app.py` | SQL injection in `/user` (CWE-89), binds to `0.0.0.0` | Semgrep (`p/ci` + `p/flask`) |
| `requirements.txt` | Flask 2.2.2, Werkzeug 2.2.2, Jinja2 3.1.2 — 3 HIGH CVEs (CVE-2023-30861, CVE-2023-25577, CVE-2024-34069) | Trivy (fs scan) |
| `Dockerfile` | No `USER` — runs as root | Trivy config (AVD-DS-0002) + image scan; Hadolint lints style |
| `k8s/deployment.yaml` | No `runAsNonRoot` | Kyverno (blocks at apply time) |
| (added live) `config.py` | Hardcoded AWS-format key | Gitleaks |
| running container | Missing security headers | OWASP ZAP baseline (report only) |

Fixed versions are provided alongside each broken file so you can swap them in
live: `app.fixed.py`, `requirements.fixed.txt`, `Dockerfile.fixed`, `k8s/deployment.fixed.yaml`.

> Notes from running this end to end:
> - Hadolint's DL3002 only fires on an explicit `USER root`; a Dockerfile with *no* `USER` passes
>   Hadolint, so the pipeline adds `trivy config` (DS002) to catch it.
> - Gitleaks allowlists AWS's documentation key `AKIAIOSFODNN7EXAMPLE`, so the leak snippet uses a
>   randomly generated (never-issued) key in the same format. On a public repo GitHub push
>   protection blocks that push first (GH013); see `LIVE_DEMO_LEAK_SNIPPET.txt`.
> - Each gate is its own job, so one failure never hides the others; the Slack job fires if any fail.

## One-time setup (do this before the talk, not live)

See `SETUP.md` for exact commands: repo + GitHub Actions secrets, local
cluster, ArgoCD, Kyverno.

## Suggested run order on stage

1. Explain the pipeline file (`.github/workflows/devsecops.yml`) stage by stage.
2. Push as-is → Semgrep, Trivy fs and the Dockerfile gate fail → Slack alert fires.
3. Add the AWS-key snippet from `LIVE_DEMO_LEAK_SNIPPET.txt` → Gitleaks fails
   → Slack alert fires again.
4. Fix one thing at a time (remove the leaked key, swap in `requirements.fixed.txt`,
   `Dockerfile.fixed`, `app.fixed.py`) → push → pipeline goes green.
5. Show ArgoCD UI already synced from `k8s/` → change replica count in Git →
   watch it auto-sync.
6. `kubectl apply -f k8s/deployment.yaml` → Kyverno rejects it (no
   `runAsNonRoot`) → then `kubectl apply -f k8s/deployment.fixed.yaml` →
   succeeds. Finally copy the fixed manifest over `k8s/deployment.yaml` in Git and let
   ArgoCD roll it out (the ArgoCD app excludes `*.fixed.yaml`, see `SETUP.md`).

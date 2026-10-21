# Setup guide (macOS)

> **Windows:** the same steps work from Git Bash with Docker Desktop. Download `kind`, `helm` and
> `argocd` as `.exe` files from their GitHub releases into a folder on your `PATH` instead of using
> Homebrew. `k8s/deployment.fixed.yaml` runs the real app image, so build and load it into kind
> first: `docker build -f Dockerfile.fixed -t demo-app:fixed .` (after `cp app.fixed.py app.py` and
> `cp requirements.fixed.txt requirements.txt`) then `kind load docker-image demo-app:fixed --name devsecops-demo`.

Do all of this now, tested end-to-end, so nothing is "first time" on stage tomorrow.

## 0. Check what you already have

```bash
docker --version
kubectl version --client
kind --version
helm version
argocd version --client
```

Anything that errors "command not found" — install it below. Skip installed ones.

## 1. Install missing tools (Homebrew)

```bash
# Install Homebrew if you don't have it
which brew || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install --cask docker        # then open Docker.app once and let it finish starting
brew install kubectl
brew install kind
brew install helm
brew install argocd
```

Open Docker Desktop and make sure it says "Docker is running" before continuing.

## 2. Create the GitHub repo

1. Go to github.com → New repository → name it e.g. `devsecops-demo` → Public (or Private, either
   works) → do NOT initialize with a README (you already have files).
2. On your machine, from the `demo-app` folder I gave you:

```bash
cd demo-app
git init
git add .
git commit -m "Initial DevSecOps demo"
git branch -M main
git remote add origin https://github.com/<your-username>/devsecops-demo.git
git push -u origin main
```

## 3. Create the Slack webhook (5 min)

1. Go to https://api.slack.com/apps → "Create New App" → "From scratch" → name it
   `devsecops-demo`, pick any workspace you have (or make a free one just for this).
2. Left sidebar → "Incoming Webhooks" → toggle it on → "Add New Webhook to Workspace" → choose
   a channel (e.g. `#general` or make `#demo-alerts`).
3. Copy the webhook URL it gives you (starts with `https://hooks.slack.com/services/...`).

## 4. Add GitHub Actions secret

In your repo on GitHub: Settings → Secrets and variables → Actions → New repository secret

- Name: `SLACK_WEBHOOK`
- Value: the webhook URL from step 3

(`GITHUB_TOKEN` used by Gitleaks is automatic — you don't need to add it.)


## 5. First test run

Push again (even an empty commit) and check the Actions tab on GitHub — you should see the
pipeline run and FAIL (on purpose, since the app is still vulnerable). Check Slack — you should
get the alert. This is your "clean baseline" — confirm it works today, not tomorrow morning.

```bash
git commit --allow-empty -m "trigger pipeline"
git push
```

## 6. Local cluster + ArgoCD

```bash
kind create cluster --name devsecops-demo

kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# wait ~1-2 min for pods to be ready, then check:
kubectl get pods -n argocd

# port-forward the UI (leave this running in its own terminal tab)
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Get the admin password:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
```

Open https://localhost:8080 (accept the self-signed cert warning), log in as `admin` with that
password.

Create the app (via CLI — or do this same thing in the UI if you prefer clicking):
```bash
argocd login localhost:8080 --username admin --password <password-from-above> --insecure

argocd app create demo-app \
  --repo https://github.com/<your-username>/devsecops-demo.git \
  --path k8s \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace default \
  --sync-policy automated
```

Refresh the ArgoCD UI — you should see `demo-app` syncing. Note: `k8s/deployment.yaml` has no
`runAsNonRoot`, so once Kyverno is installed (next step) ArgoCD's sync may show the pod as
degraded/blocked — that's expected and is actually part of the demo (point it out live rather
than "fixing" it beforehand).

## 7. Install Kyverno

```bash
kubectl create namespace kyverno
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update
helm install kyverno kyverno/kyverno -n kyverno

# wait for it to be ready
kubectl get pods -n kyverno
```

Apply the policy:
```bash
kubectl apply -f kyverno/disallow-root.yaml
```

## 8. Test the Kyverno block (do this today, not live for the first time)

```bash
kubectl apply -f k8s/deployment.yaml
```
Expect this to be REJECTED with a message about `runAsNonRoot`. That rejection message on
screen is the demo moment.

Then:
```bash
kubectl apply -f k8s/deployment.fixed.yaml
```
Expect this to succeed.

Once you've confirmed both, revert to the broken one in Git so ArgoCD/the repo is back in the
"broken" state for tomorrow's live walkthrough:
```bash
cp k8s/deployment.yaml /tmp/backup-fixed-test.yaml   # optional, just to be safe
git status   # deployment.yaml in git should already be the broken version, untouched
```

## Day-of checklist

- [ ] Docker Desktop open and running
- [ ] `kind get clusters` shows `devsecops-demo`
- [ ] `kubectl port-forward svc/argocd-server -n argocd 8080:443` running in a terminal tab
- [ ] ArgoCD UI reachable at https://localhost:8080, `demo-app` visible
- [ ] Slack channel open on a visible tab/screen so alerts pop live
- [ ] GitHub repo Actions tab open in a browser tab
- [ ] Terminal ready in the `demo-app` folder, `LIVE_DEMO_LEAK_SNIPPET.txt` open for copy-paste

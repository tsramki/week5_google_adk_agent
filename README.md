# Agent Hub (Google ADK)

Three agents built with the [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/), served from one Streamlit app with a project selector in the sidebar:

| Project | What it does | Details |
|---|---|---|
| Teaching Assistant | Researches resources with Google Search and builds a personalized learning plan | below |
| Health Assistant | Interprets lab results and gives lifestyle and follow-up recommendations | [HEALTH_ASSISTANT.md](HEALTH_ASSISTANT.md) |
| Financial Planner | Reviews household finances and builds a plan for the future | [FINANCIAL_PLANNER.md](FINANCIAL_PLANNER.md) |

The health and financial agents are educational only, not medical or financial advice.

## Project structure

```text
google_adk_agent/
├── hub.py                       # Entry point: password gate + project selector
├── teaching_assistant_app.py    # Streamlit UI per project (pages of the hub)
├── app.py                       #   health assistant UI
├── financial_planner_app.py
├── ui_common.py                 # Shared helper that runs an ADK agent from Streamlit
├── teaching_assistant/          # Agent packages (also discovered by `adk web`)
├── health_assistant/            #   each: __init__.py, agent.py, .env, .env.example
├── financial_planner/           #   health and financial also have analysis.py
├── Dockerfile                   # Container image for Cloud Run (runs hub.py)
├── requirements.txt             # google-adk, streamlit
├── .dockerignore
└── .venv/                       # Local virtual environment (not deployed)
```

Each agent's calculations (reference ranges, ratios, projections) live in plain Python in its `analysis.py`, exposed to the model as a tool, so the LLM never does the arithmetic. The teaching assistant uses the built-in `google_search` tool, which cannot be combined with custom function tools in the same agent.

| Environment variable | Required | Purpose |
|---|---|---|
| `APP_PASSWORD` | on Cloud Run | Password for the sign-in page. Locally it is optional; on Cloud Run (`K_SERVICE` set) the app refuses to serve without it. |
| `PORT` | no | Port to listen on (Cloud Run sets it; the container defaults to 8080). |

This is a single shared password, not per-user accounts, and it has no rate limiting. Use a long random password. Do not enter real health or financial data into a deployment you have not secured to your satisfaction.

## Local development

Requires Python 3.10+.

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

### Credentials

Pick one. Each agent reads `<agent>/.env` (beside its `agent.py`).

**Google AI Studio key** (simplest locally), from https://aistudio.google.com/app/apikey:

```bash
GOOGLE_GENAI_USE_ENTERPRISE=FALSE
GOOGLE_API_KEY=YOUR_API_KEY
```

**Vertex AI** (what the deployed service uses). Run `gcloud auth application-default login` with an account that has `roles/aiplatform.user`, then:

```bash
GOOGLE_GENAI_USE_ENTERPRISE=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
```

### Run

```bash
.venv/bin/streamlit run hub.py          # all three, with a project selector
.venv/bin/streamlit run app.py          # or one project's UI alone
.venv/bin/adk web .                     # ADK's generic chat UI (debugging; no custom UI)
```

The hub opens at http://localhost:8501. Add `APP_PASSWORD=testpw` to test the sign-in page.

## Deployment (Google Cloud Run)

One service runs the whole hub. It builds from source with the Dockerfile, calls Gemini through Vertex AI using the service account (no API key in the deployment), and reads the password from Secret Manager.

| Setting | Value |
|---|---|
| Project | `gen-lang-client-0928202266` |
| Region | `us-west1` |
| Service name | `agent-hub` |
| Model location | `global` (set in each agent's `.env`) |
| Secret | `agent-hub-password` (mounted as `APP_PASSWORD`) |

### One-time setup

```bash
export CLOUDSDK_CORE_ACCOUNT=<email>
export CLOUDSDK_CORE_PROJECT=<projectId>
P=$CLOUDSDK_CORE_PROJECT

gcloud services enable aiplatform.googleapis.com secretmanager.googleapis.com

# Password secret. Save the printed password somewhere safe.
PW=$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-24)
printf '%s' "$PW" | gcloud secrets create agent-hub-password \
  --data-file=- --replication-policy=automatic
echo "Password: $PW"

# Let the runtime service account call Gemini and read the secret
NUM=$(gcloud projects describe $P --format='value(projectNumber)')
SA=$NUM-compute@developer.gserviceaccount.com
gcloud projects add-iam-policy-binding $P \
  --member=serviceAccount:$SA --role=roles/aiplatform.user --condition=None
gcloud secrets add-iam-policy-binding agent-hub-password \
  --member=serviceAccount:$SA --role=roles/secretmanager.secretAccessor

# This project's default compute service account was disabled; Cloud Build and
# Cloud Run both use it, so it must be enabled before deploying.
gcloud iam service-accounts enable $SA
```

### Deploy

Run from the project root, because `--source .` uploads the current directory:

```bash
cd /Users/ramakrishnaseshadri/Documents/agentAI/Week5/google_adk_agent

gcloud run deploy agent-hub \
  --source . \
  --region us-west1 \
  --allow-unauthenticated \
  --max-instances 2 \
  --session-affinity \
  --set-secrets APP_PASSWORD=agent-hub-password:latest
```

`--allow-unauthenticated` makes the service reachable from the internet; the sign-in page in `hub.py` is the only gate. `--max-instances 2` caps cost. `--session-affinity` keeps a browser on one instance, because Streamlit sessions and the agents' conversations live in that instance's memory.

### Retire the old teaching-assistant service

After `agent-hub` works:

```bash
gcloud run services delete teaching-assistant --region us-west1
gcloud secrets delete teaching-assistant-password
```

### Verify

```bash
URL=$(gcloud run services describe agent-hub --region us-west1 --format='value(status.url)')
curl -s -o /dev/null -w "%{http_code}\n" $URL/_stcore/health   # 200
```

Then open the URL, sign in with the password, and switch projects in the sidebar.

### Operations

```bash
gcloud run services logs read agent-hub --region us-west1

# Rotate the password, then restart so the service picks up `latest`
printf '%s' "NEW_PASSWORD" | gcloud secrets versions add agent-hub-password --data-file=-
gcloud run services update agent-hub --region us-west1 --update-env-vars=RESTARTED_AT=$(date +%s)

# Tear down
gcloud run services delete agent-hub --region us-west1
gcloud secrets delete agent-hub-password
```

Sessions are in memory, so they are lost when an instance restarts or scales to zero.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Provided service account (...-compute@developer.gserviceaccount.com) is disabled` during deploy | Re-enable it with `gcloud iam service-accounts enable <SA>`, or create a dedicated service account and pass `--service-account` and `--build-service-account`. |
| "APP_PASSWORD is not configured; refusing to serve" | The secret is not mounted. Check the `--set-secrets` flag and that the service account has Secret Accessor. |
| `403 PERMISSION_DENIED ... aiplatform.endpoints.predict` in the chat | The identity running the app lacks `roles/aiplatform.user` (locally, your `gcloud` account; deployed, the service account), or use an AI Studio key locally. |
| UI loads but stays on "Please wait" / reconnects | WebSockets are blocked or session affinity is off. Check that the deploy used the flags above. |
| Agent missing from the `adk web` dropdown | The package's `__init__.py` lacks `from . import agent`, or `agent.py` defines no `root_agent`. |
| API key errors locally | `.env` is in the project root instead of inside the agent's folder. |
| Service URL returns 403 before the sign-in page | An organization policy is blocking public access (`--allow-unauthenticated`). |

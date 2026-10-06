# Teaching Assistant Agent

A teaching assistant built with the [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/). A student names a skill they want to learn, and the agent researches current resources with Google Search and returns a personalized learning plan: assumptions, a phased roadmap with practice projects, resources with links, milestones, and tips.

## Project structure

```text
google_adk_agent/
├── teaching_assistant/        # The agent package (what `adk web` discovers)
│   ├── __init__.py            # `from . import agent` (required for discovery)
│   ├── agent.py               # Defines `root_agent`: model, instruction, tools
│   ├── .env                   # Vertex AI settings (project, location); no secrets
│   └── .env.example           # Template for local use with an AI Studio API key
├── main.py                    # Production server: ADK web UI + API behind Basic auth
├── Dockerfile                 # Container image for Cloud Run
├── requirements.txt           # Runtime dependencies (google-adk)
├── .dockerignore              # Keeps .venv and local files out of the image
├── skills-lock.json           # Lockfile written by the `skills` CLI (not used at runtime)
└── .venv/                     # Local virtual environment (not deployed)
```

### The agent

[teaching_assistant/agent.py](teaching_assistant/agent.py) defines a single `Agent` using `gemini-2.5-flash` and the built-in `google_search` tool. Its instruction tells it to:

1. Ask what skill the student wants (if not given).
2. Ask at most three quick questions: current level, weekly time, goal or deadline. It skips them if the student already answered or asks for a plan straight away.
3. Research reputable resources with Google Search and never invent links.
4. Reply with the plan and offer to adjust it.

`google_search` is a Gemini built-in tool. It works with Gemini 2.x models but cannot be combined with custom function tools in the same agent. If you need custom tools later, wrap search in a sub-agent.

### The production server

[main.py](main.py) builds the ADK FastAPI app (`get_fast_api_app(..., web=True)`) and wraps it in a small pure-ASGI middleware that enforces HTTP Basic auth on every HTTP and WebSocket request, including the API. Browsers show a native login prompt. Because it is plain ASGI, streaming (SSE) responses are not buffered.

| Environment variable | Required | Default | Purpose |
|---|---|---|---|
| `APP_PASSWORD` | yes | none | Password for the Basic auth login. The server refuses to start without it. |
| `APP_USERNAME` | no | `student` | Login username. |
| `PORT` | no | `8080` | Port to listen on (Cloud Run sets this). |

This is a single shared password, not per-user accounts, and it has no rate limiting. Use a long random password.

## Local development

### Setup

Requires Python 3.10+.

```bash
uv venv .venv
uv pip install --python .venv/bin/python google-adk
# or: python -m venv .venv && .venv/bin/pip install google-adk
```

### Credentials

Pick one. Both go in `teaching_assistant/.env` (the file must be beside `agent.py`).

**Google AI Studio key** (simplest locally). Get a key at https://aistudio.google.com/app/apikey:

```bash
GOOGLE_GENAI_USE_ENTERPRISE=FALSE
GOOGLE_API_KEY=YOUR_API_KEY
```

**Vertex AI** (what the deployed service uses). Run `gcloud auth application-default login`, then:

```bash
GOOGLE_GENAI_USE_ENTERPRISE=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
```

### Run with `adk web`

From the project root:

```bash
.venv/bin/adk web .
```

Open http://localhost:8000, choose `teaching_assistant`, and try: *"I want to learn guitar, 5 hours a week."*

Other useful commands:

```bash
.venv/bin/adk run teaching_assistant    # chat in the terminal
```

### Test the password-protected server locally

```bash
APP_PASSWORD=testpw PORT=8080 .venv/bin/python main.py
curl -s -o /dev/null -w "%{http_code}\n" localhost:8080/                    # 401
curl -s -o /dev/null -w "%{http_code}\n" -u student:testpw localhost:8080/  # 307 (redirect to the UI)
```

## Deployment (Google Cloud Run)

The service runs on Cloud Run, builds from source with the included Dockerfile, authenticates to Gemini through Vertex AI using the service account (no API key in the deployment), and reads the login password from Secret Manager.

| Setting | Value |
|---|---|
| Project | `<project>` |
| Region | `<region>` |
| Service name | `teaching-assistant` |
| Model location | `global` (set in `teaching_assistant/.env`) |
| Secret | `teaching-assistant-password` (mounted as `APP_PASSWORD`) |

### One-time setup

```bash
export CLOUDSDK_CORE_ACCOUNT=<email>
export CLOUDSDK_CORE_PROJECT=<projectId>
P=$CLOUDSDK_CORE_PROJECT

# APIs (run, cloudbuild and artifactregistry were already enabled)
gcloud services enable aiplatform.googleapis.com secretmanager.googleapis.com

# Password secret. Save the printed password somewhere safe.
PW=$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-24)
printf '%s' "$PW" | gcloud secrets create teaching-assistant-password \
  --data-file=- --replication-policy=automatic
echo "Username: student   Password: $PW"

# Let the runtime service account call Gemini and read the secret
NUM=$(gcloud projects describe $P --format='value(projectNumber)')
SA=$NUM-compute@developer.gserviceaccount.com
gcloud projects add-iam-policy-binding $P \
  --member=serviceAccount:$SA --role=roles/aiplatform.user --condition=None
gcloud secrets add-iam-policy-binding teaching-assistant-password \
  --member=serviceAccount:$SA --role=roles/secretmanager.secretAccessor

# This project's default compute service account was disabled; Cloud Build and
# Cloud Run both use it, so it must be enabled before deploying.
gcloud iam service-accounts enable $SA
```

### Deploy

Run from the project root, because `--source .` uploads the current directory:

```bash
cd /Users/ramakrishnaseshadri/Documents/agentAI/Week5/google_adk_agent

gcloud run deploy teaching-assistant \
  --source . \
  --region <region> \
  --allow-unauthenticated \
  --max-instances 2 \
  --set-secrets APP_PASSWORD=teaching-assistant-password:latest
```

`--allow-unauthenticated` makes the service reachable from the internet. The Basic auth in `main.py` is the only gate. `--max-instances 2` caps cost.

### Verify

```bash
URL=$(gcloud run services describe teaching-assistant --region <region> --format='value(status.url)')
curl -s -o /dev/null -w "%{http_code}\n" $URL                    # 401
curl -s -o /dev/null -w "%{http_code}\n" -u "student:$PW" $URL   # 200 or 307
```

Then open the URL in a browser and log in as `student`.

### Operations

```bash
# Logs
gcloud run services logs read teaching-assistant --region <region>

# Rotate the password, then restart so the service picks up `latest`
printf '%s' "NEW_PASSWORD" | gcloud secrets versions add teaching-assistant-password --data-file=-
gcloud run services update teaching-assistant --region <region> --update-env-vars=RESTARTED_AT=$(date +%s)

# Tear down
gcloud run services delete teaching-assistant --region <region>
gcloud secrets delete teaching-assistant-password
```

Sessions are stored in memory, so they are lost when an instance restarts or scales to zero.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Agent missing from the `adk web` dropdown | `teaching_assistant/__init__.py` lacks `from . import agent`, or `agent.py` defines no `root_agent`. |
| API key errors locally | `.env` is in the project root instead of `teaching_assistant/`. |
| Service URL returns 403 before the login prompt | An organization policy is blocking public access (`--allow-unauthenticated`). |
| Model or location errors in the deployed service | Check the logs. The location is set by `GOOGLE_CLOUD_LOCATION` in `teaching_assistant/.env`. |
| `APP_PASSWORD` KeyError at startup | The secret is not mounted. Check the `--set-secrets` flag and that the service account has Secret Accessor. |

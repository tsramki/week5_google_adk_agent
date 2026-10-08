# Health Assistant

An ADK agent that interprets lab results and gives personalized, educational recommendations. Same layout as `teaching_assistant`, plus a Streamlit UI.

```text
health_assistant/
├── agent.py      # root_agent (Gemini) + analyze_health_data tool
├── analysis.py   # deterministic reference-range logic (no LLM)
├── .env          # Vertex AI settings (copied from teaching_assistant)
└── .env.example  # AI Studio key template
app.py            # Streamlit UI: form -> range dashboard -> AI recommendations -> follow-up chat
```

**Inputs:** name, age, sex, weight, height (metric or US), medications, and any of HDL, LDL, triglycerides, VLDL, total cholesterol, ApoB, Lp(a), HbA1c, fasting glucose, RBC, WBC, Hgb, PLT, ALT, AST, eGFR, TSH. Units are US conventional (mg/dL etc.).

**Design:** the agent calls `analyze_health_data`, which classifies each value against adult reference ranges in `analysis.py`, so range judgments are never left to the LLM. The UI shows the same classification instantly as color-coded cards, while the agent writes the narrative: summary, findings, patterns across markers, lifestyle steps, medication considerations, doctor questions and red flags. It never advises changing medication.

## Run

```bash
.venv/bin/streamlit run app.py        # the polished UI
.venv/bin/adk web .                   # or the generic ADK chat UI (pick health_assistant)
```

Credentials: either run `gcloud auth application-default login` with an account that has `roles/aiplatform.user` on the project in `health_assistant/.env`, or put `GOOGLE_API_KEY` in that file (see `.env.example`).

Not a medical device. Reference ranges are general adult values and vary by lab.

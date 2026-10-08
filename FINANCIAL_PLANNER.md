# Financial Planner

An ADK agent that reviews a US household's finances and builds a prioritized plan. Same layout as `teaching_assistant` and `health_assistant`.

```text
financial_planner/
├── agent.py      # root_agent (Gemini) + analyze_finances tool
├── analysis.py   # deterministic calculations and benchmarks (no LLM)
├── .env          # Vertex AI settings (copied from teaching_assistant)
└── .env.example  # AI Studio key template
financial_planner_app.py   # Streamlit UI: guided form -> dashboard -> AI plan -> follow-up chat
```

**Inputs:** age, retirement age, dependents, household gross income, monthly take-home and spending; checking, savings, stocks, bonds, home value, investment real estate, 401(k), IRA, other assets; mortgage, student, credit card (with APR), auto and other debt, monthly debt payments; 401(k) contribution and employer match; risk tolerance; insurance and will; goals.

**What `analysis.py` computes:** net worth, emergency-fund months, debt-to-income, savings rate, 401(k) match gap, retirement savings vs. age benchmarks, a real-dollar retirement projection with the monthly saving needed to close any gap, allocation breakdown, and insurance/estate gaps. 2026 contribution limits are constants at the top of the file; review them each January. Assumptions (real return by risk level, 4% withdrawal rate, Social Security covering 25% of spending) are returned with every analysis and shown in the UI.

**The agent** gathers missing information in at most three short messages, calls the tool, then writes: snapshot, strengths, concerns, a prioritized action plan (match -> emergency fund -> high-interest debt -> tax-advantaged accounts -> other goals), a 90-day / 1 / 5 year / retirement roadmap, investment principles (no specific securities), protection gaps, and questions for a professional. It ends with a disclaimer.

## Run

```bash
.venv/bin/streamlit run financial_planner_app.py   # the polished UI
.venv/bin/adk web .                                 # or the generic chat UI (pick financial_planner)
```

Credentials are the same as the other projects: an AI Studio `GOOGLE_API_KEY` in `financial_planner/.env`, or Vertex AI with `roles/aiplatform.user`.

Not financial, investment, tax or legal advice.

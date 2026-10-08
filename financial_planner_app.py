"""Streamlit UI for the financial planner.

A guided form collects household finances, a deterministic dashboard shows the
numbers immediately, and the ADK agent writes the review and future plan and
answers follow-up questions.

Run:  .venv/bin/streamlit run financial_planner_app.py
"""

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'financial_planner', '.env'))

from google.adk.runners import InMemoryRunner  # noqa: E402

from ui_common import ask, set_page_config  # noqa: E402
from financial_planner.agent import root_agent  # noqa: E402
from financial_planner.analysis import analyze  # noqa: E402

APP_NAME = 'financial_planner'
STATUS_STYLE = {
    'good': ('#1b7f4c', '#e3f5ea', 'On track'),
    'watch': ('#9a6700', '#fff4d6', 'Watch'),
    'action': ('#b42318', '#fde4e1', 'Needs action'),
}

set_page_config(page_title='Financial Planner', page_icon='💼', layout='wide')
st.markdown(
    """
    <style>
    .block-container {max-width: 1200px; padding-top: 2rem;}
    .card {border-radius: 12px; padding: 12px 14px; margin-bottom: 10px;
           border: 1px solid rgba(128,128,128,.25); color:#1a1a1a;}
    .card .area {font-size: .75rem; opacity: .7; text-transform: uppercase; letter-spacing:.04em;}
    .card .head {font-size: 1.02rem; font-weight: 650; line-height: 1.25; margin: 2px 0 4px;}
    .card .det {font-size: .8rem; opacity: .85;}
    .pill {display:inline-block; font-size:.72rem; font-weight:600;
           padding:2px 8px; border-radius:999px; margin-bottom:4px; color:#fff;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def _runner() -> InMemoryRunner:
  return InMemoryRunner(agent=root_agent, app_name=APP_NAME)


def _ask(prompt: str) -> str:
  return ask(_runner(), APP_NAME, 'fin_adk_session', prompt)


def money(label: str, key: str, help: str | None = None):
  return st.number_input(label, min_value=0.0, value=0.0, step=100.0, format='%.0f',
                         key=key, help=help)


def usd(v: float) -> str:
  return f'-${-v:,.0f}' if v < 0 else f'${v:,.0f}'


def _build_prompt(d: dict, extra: dict) -> str:
  lines = '\n'.join(f'- {k}: {v}' for k, v in d.items())
  return (
      f"Name: {extra['name'] or 'not given'}\nGoals: {extra['goals'] or 'none stated'}\n\n"
      f'Here is my financial information (USD; 0 means none):\n{lines}\n\n'
      'Please review my situation and give me a plan for my financial future.'
  )


st.title('💼 Financial Planner')
st.caption(
    'Tell us about your household finances for an instant snapshot and a '
    'personalized AI-written review and plan. Estimates are fine. Nothing is stored.'
)

with st.form('fin_form'):
  tabs = st.tabs(['1 · You', '2 · Assets', '3 · Debts', '4 · Retirement & protection', '5 · Goals'])

  with tabs[0]:
    c1, c2, c3 = st.columns(3)
    name = c1.text_input('Name (optional)')
    age = c2.number_input('Your age', 18, 100, value=None, step=1)
    retirement_age = c3.number_input('Target retirement age', 40, 90, value=65, step=1)
    c4, c5, c6 = st.columns(3)
    dependents = c4.number_input('Dependents', 0, 20, value=0, step=1)
    with c5:
      income = money('Household annual gross income ($)', 'income')
    risk = c6.selectbox('Investing style', ['Conservative', 'Moderate', 'Aggressive'], index=1)
    c7, c8 = st.columns(2)
    with c7:
      take_home = money('Monthly take-home pay, after tax ($)', 'take_home')
    with c8:
      expenses = money('Monthly spending, all-in ($)', 'expenses',
                       'Housing, food, transport, subscriptions, debt payments: everything you spend.')

  with tabs[1]:
    st.caption('Current balances. Leave 0 if you do not have it.')
    a1, a2, a3 = st.columns(3)
    with a1:
      checking = money('Checking ($)', 'checking')
      stocks = money('Stocks / funds / ETFs, taxable ($)', 'stocks')
      retirement_401k = money('401(k) / 403(b) / TSP ($)', 'k401')
    with a2:
      savings = money('Savings / money market / CDs ($)', 'savings')
      bonds = money('Bonds, taxable ($)', 'bonds')
      ira = money('IRA / Roth IRA ($)', 'ira')
    with a3:
      home_value = money('Primary home value ($)', 'home')
      inv_re = money('Rental / investment real estate ($)', 'inv_re')
      other_assets = money('Other: HSA, crypto, business… ($)', 'other_assets')

  with tabs[2]:
    d1, d2, d3 = st.columns(3)
    with d1:
      mortgage = money('Mortgage balance(s) ($)', 'mortgage')
      student = money('Student loans ($)', 'student')
    with d2:
      cc = money('Credit card balance carried ($)', 'cc')
      auto = money('Auto loans ($)', 'auto')
    with d3:
      cc_apr = st.number_input('Credit card APR (%)', 0.0, 40.0, value=0.0, step=0.5)
      other_debt = money('Other debt ($)', 'other_debt')
    debt_pay = money('Total monthly debt payments incl. mortgage ($)', 'debt_pay')

  with tabs[3]:
    r1, r2 = st.columns(2)
    k_pct = r1.number_input('Your 401(k) contribution (% of salary)', 0.0, 100.0, value=0.0, step=1.0)
    match = r2.number_input('Employer match: up to (% of salary)', 0.0, 100.0, value=0.0, step=0.5,
                            help='The percent of salary your employer will match if you contribute.')
    desired = money('Desired annual spending in retirement, today\'s dollars ($, 0 = estimate)', 'desired')
    p1, p2, p3 = st.columns(3)
    with p1:
      life = money('Life insurance coverage ($)', 'life')
    disability = p2.checkbox('I have disability insurance')
    will = p3.checkbox('I have a will / estate documents')

  with tabs[4]:
    goals = st.text_area(
        'Goals & concerns (optional)',
        placeholder='e.g. buy a bigger house in 5 years, college for two kids, retire at 60, pay off student loans',
        height=120,
    )

  submitted = st.form_submit_button('Review my finances', type='primary', use_container_width=True)

if submitted:
  if not age or not income:
    st.error('Please enter at least your age and household annual gross income.')
  else:
    data = dict(
        age=int(age), retirement_age=int(retirement_age), annual_gross_income=income,
        monthly_take_home=take_home, monthly_expenses=expenses, dependents=int(dependents),
        checking=checking, savings=savings, stocks=stocks, bonds=bonds, home_value=home_value,
        investment_real_estate=inv_re, retirement_401k=retirement_401k, ira=ira,
        other_assets=other_assets, mortgage_balance=mortgage, student_loans=student,
        credit_card_debt=cc, auto_loans=auto, other_debt=other_debt,
        monthly_debt_payments=debt_pay, credit_card_apr=cc_apr, contribution_401k_pct=k_pct,
        employer_match_pct=match, risk_tolerance=risk.lower(),
        desired_retirement_spending=desired, life_insurance_coverage=life,
        has_disability_insurance=disability, has_will=will,
    )
    st.session_state['fin_adk_session'] = None
    st.session_state['fin_result'] = analyze(**data)
    st.session_state['fin_name'] = name.strip()
    st.session_state['fin_chat'] = []
    with st.spinner('Building your plan…'):
      try:
        reply = _ask(_build_prompt(data, {'name': name.strip(), 'goals': goals.strip()}))
      except Exception as e:  # surface credential/model errors in the UI
        reply = f'⚠️ Could not reach the model: `{e}`'
    st.session_state['fin_chat'].append(('assistant', reply))

r = st.session_state.get('fin_result')
if r:
  st.divider()
  who = st.session_state.get('fin_name')
  st.header(f'Snapshot for {who}' if who else 'Your snapshot')
  m = st.columns(5)
  m[0].metric('Net worth', usd(r['net_worth']))
  m[1].metric('Assets', usd(r['total_assets']))
  m[2].metric('Liabilities', usd(r['total_liabilities']))
  m[3].metric('Emergency fund', f"{r['emergency_fund_months']} mo" if r['emergency_fund_months'] is not None else '–')
  m[4].metric('Savings rate', f"{r['savings_rate']:.0%}" if r['savings_rate'] is not None else '–')

  left, right = st.columns([1, 1])
  with left:
    st.subheader('Retirement outlook')
    p = r['projection']
    if p['target_nest_egg']:
      st.progress(min(int(p['on_track_pct'] or 0), 100) / 100,
                  text=f"{p['on_track_pct']:.0f}% of target projected at retirement")
      st.markdown(
          f"Projected **{usd(p['projected_balance_todays_dollars'])}** vs. target "
          f"**{usd(p['target_nest_egg'])}** (today's dollars, {p['years_to_retirement']} years away)."
      )
      if p['shortfall']:
        st.markdown(f"Gap: **{usd(p['shortfall'])}** — about **{usd(p['extra_monthly_saving_to_close_gap'])}/month** more would close it.")
    with st.expander('Assumptions'):
      for a in r['assumptions']:
        st.markdown(f'- {a}')
  with right:
    st.subheader('Where your assets sit')
    if r['allocation_pct']:
      st.bar_chart(r['allocation_pct'], horizontal=True, y_label='% of financial assets')
      if r['allocation_guideline']:
        st.caption(f"Guide: {r['allocation_guideline']}")

  st.subheader('What the numbers say')
  cols = st.columns(2)
  for i, f in enumerate(r['findings']):
    fg, bg, label = STATUS_STYLE[f['status']]
    with cols[i % 2]:
      st.markdown(
          f"""<div class="card" style="background:{bg}">
          <span class="pill" style="background:{fg}">{label}</span>
          <div class="area">{f['area']}</div>
          <div class="head">{f['headline']}</div>
          <div class="det">{f['detail']}</div></div>""",
          unsafe_allow_html=True,
      )

  st.subheader('Your plan')
  for role, text in st.session_state['fin_chat']:
    with st.chat_message(role):
      st.markdown(text)
  follow = st.chat_input('Ask a follow-up (e.g. "What if I retire at 60?" or "How should I pay off my debts?")')
  if follow:
    st.session_state['fin_chat'].append(('user', follow))
    with st.chat_message('user'):
      st.markdown(follow)
    with st.chat_message('assistant'):
      with st.spinner('Thinking…'):
        try:
          reply = _ask(follow)
        except Exception as e:
          reply = f'⚠️ Could not reach the model: `{e}`'
      st.markdown(reply)
    st.session_state['fin_chat'].append(('assistant', reply))
  st.caption('Disclaimer: This information is for informational and educational purposes only and is not financial, investment, tax, or legal advice. Please consult a qualified financial professional before making any financial decisions.')

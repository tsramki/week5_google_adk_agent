"""Streamlit UI for the health assistant.

A structured form collects the profile and labs, a deterministic dashboard
shows each marker against its reference range immediately, and the ADK agent
writes personalized recommendations and answers follow-up questions.

Run:  .venv/bin/streamlit run app.py
"""

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'health_assistant', '.env'))

from google.adk.runners import InMemoryRunner  # noqa: E402

from ui_common import ask, set_page_config  # noqa: E402
from health_assistant.agent import root_agent  # noqa: E402
from health_assistant.analysis import MARKERS, SEVERITY, analyze  # noqa: E402

APP_NAME = 'health_assistant'
STATUS_STYLE = {
    'normal': ('#1b7f4c', '#e3f5ea', 'In range'),
    'borderline': ('#9a6700', '#fff4d6', 'Borderline'),
    'low': ('#b35900', '#ffe9d2', 'Low'),
    'high': ('#b42318', '#fde4e1', 'High'),
    'very high': ('#7a1010', '#f9c9c4', 'Very high'),
}

# (label, key, min, max, step, format) grouped for the form.
LAB_GROUPS = {
    'Cholesterol & lipids': [
        ('Total cholesterol', 'total_cholesterol', 50.0, 600.0, 1.0, '%.0f'),
        ('LDL', 'ldl', 10.0, 400.0, 1.0, '%.0f'),
        ('HDL', 'hdl', 5.0, 150.0, 1.0, '%.0f'),
        ('Triglycerides', 'triglycerides', 20.0, 2000.0, 1.0, '%.0f'),
        ('VLDL', 'vldl', 1.0, 200.0, 1.0, '%.0f'),
        ('ApoB', 'apob', 10.0, 250.0, 1.0, '%.0f'),
        ('Lipoprotein(a)', 'lpa', 0.0, 500.0, 1.0, '%.0f'),
    ],
    'Blood sugar': [
        ('HbA1c', 'hba1c', 3.0, 15.0, 0.1, '%.1f'),
        ('Fasting glucose (FBS/FBG)', 'fbg', 30.0, 600.0, 1.0, '%.0f'),
    ],
    'Blood count': [
        ('RBC', 'rbc', 1.0, 9.0, 0.1, '%.2f'),
        ('WBC', 'wbc', 0.5, 50.0, 0.1, '%.1f'),
        ('Hemoglobin (Hgb)', 'hgb', 3.0, 25.0, 0.1, '%.1f'),
        ('Platelets (PLT)', 'plt', 10.0, 1500.0, 1.0, '%.0f'),
    ],
    'Liver, kidney & thyroid': [
        ('ALT', 'alt', 1.0, 2000.0, 1.0, '%.0f'),
        ('AST', 'ast', 1.0, 2000.0, 1.0, '%.0f'),
        ('eGFR', 'egfr', 1.0, 200.0, 1.0, '%.0f'),
        ('TSH', 'tsh', 0.0, 100.0, 0.01, '%.2f'),
    ],
}

set_page_config(page_title='Health Assistant', page_icon='🩺', layout='wide')
st.markdown(
    """
    <style>
    .block-container {max-width: 1200px; padding-top: 2rem;}
    .card {border-radius: 12px; padding: 12px 14px; margin-bottom: 10px;
           border: 1px solid rgba(128,128,128,.25);}
    .card .name {font-size: .8rem; opacity: .75;}
    .card .val {font-size: 1.5rem; font-weight: 650; line-height: 1.2;}
    .card .unit {font-size: .75rem; opacity: .7; margin-left: 4px;}
    .pill {display:inline-block; font-size:.72rem; font-weight:600;
           padding:2px 8px; border-radius:999px; margin-top:4px;}
    .ref {font-size:.72rem; opacity:.7; margin-top:4px;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def _runner() -> InMemoryRunner:
  return InMemoryRunner(agent=root_agent, app_name=APP_NAME)


def _ask(prompt: str) -> str:
  return ask(_runner(), APP_NAME, 'health_adk_session', prompt)


def _cards(findings: list[dict]) -> None:
  cols = st.columns(4)
  for i, f in enumerate(sorted(findings, key=lambda f: -SEVERITY[f['status']])):
    fg, bg, label = STATUS_STYLE[f['status']]
    with cols[i % 4]:
      st.markdown(
          f"""<div class="card" style="background:{bg}; color:#1a1a1a">
          <div class="name">{f['marker']}</div>
          <div><span class="val">{f['value']:g}</span><span class="unit">{f['unit']}</span></div>
          <span class="pill" style="background:{fg}; color:#fff">{label}</span>
          <div class="ref">{f['interpretation']} · ref {f['reference']}</div>
          </div>""",
          unsafe_allow_html=True,
      )


def _build_prompt(p: dict, labs: dict[str, float]) -> str:
  lab_lines = '\n'.join(
      f'- {MARKERS[k][0]}: {v:g} {MARKERS[k][1]}' for k, v in labs.items()
  )
  return (
      f"Name: {p['name']}\nAge: {p['age']}\nSex: {p['sex']}\n"
      f"Weight: {p['weight_kg']:.1f} kg\nHeight: {p['height_cm']:.1f} cm\n"
      f"Medications/supplements: {p['meds'] or 'none'}\n\n"
      f"Latest labs:\n{lab_lines}\n\n"
      'Please analyze these and give me recommendations.'
  )


# ---------------------------------------------------------------- header
st.title('🩺 Health Assistant')
st.caption(
    'Enter your latest lab results for an instant range check and AI-written, '
    'personalized recommendations. Educational only, not medical advice.'
)

# ------------------------------------------------------------------ form
# Outside the form so changing it reruns immediately and relabels the fields.
units = st.radio('Units for Weight & Height', ['Metric (kg, cm)', 'US (lb, in)'], horizontal=True)
us = units.startswith('US')
with st.form('health_form'):
  st.subheader('About you')
  c1, c2, c3 = st.columns([2, 1, 1])
  name = c1.text_input('Name')
  age = c2.number_input('Age', 18, 120, value=None, step=1)
  sex = c3.selectbox('Sex', ['Female', 'Male'], index=None, placeholder='Select')
  c5, c6 = st.columns(2)
  weight = c5.number_input(f"Weight ({'lb' if us else 'kg'})", 1.0, 1000.0, value=None, step=0.5)
  height = c6.number_input(f"Height ({'in' if us else 'cm'})", 10.0, 120.0 if us else 250.0, value=None, step=0.5)
  meds = st.text_area(
      'Medications & supplements (one per line or comma-separated, include doses if you know them)',
      placeholder='e.g. atorvastatin 20 mg, metformin 500 mg, vitamin D',
      height=80,
  )

  st.subheader('Latest lab results')
  st.caption('Fill in only the tests you have. Units are shown in each label.')
  tabs = st.tabs(list(LAB_GROUPS))
  lab_inputs: dict[str, float | None] = {}
  for tab, (group, items) in zip(tabs, LAB_GROUPS.items()):
    with tab:
      cols = st.columns(3)
      for i, (label, key, lo, hi, step, fmt) in enumerate(items):
        lab_inputs[key] = cols[i % 3].number_input(
            f'{label} ({MARKERS[key][1]})', lo, hi, value=None, step=step,
            format=fmt, key=f'lab_{key}',
        )
  submitted = st.form_submit_button('Analyze my results', type='primary', use_container_width=True)

if submitted:
  labs = {k: v for k, v in lab_inputs.items() if v is not None}
  missing = [n for n, v in [('name', name), ('age', age), ('sex', sex), ('weight', weight), ('height', height)] if not v]
  if missing:
    st.error('Please fill in: ' + ', '.join(missing))
  elif not labs:
    st.error('Enter at least one lab value.')
  else:
    weight_kg = weight * 0.45359237 if us else weight
    height_cm = height * 2.54 if us else height
    profile = dict(name=name.strip(), age=int(age), sex=sex, weight_kg=weight_kg,
                   height_cm=height_cm, meds=meds.strip())
    # Fresh conversation for each new submission.
    st.session_state['health_adk_session'] = None
    st.session_state['result'] = analyze(labs, sex.lower(), weight_kg, height_cm)
    st.session_state['profile'] = profile
    st.session_state['health_chat'] = []
    with st.spinner('Reviewing your results…'):
      try:
        reply = _ask(_build_prompt(profile, labs))
      except Exception as e:  # surface credential/model errors in the UI
        reply = f'⚠️ Could not reach the model: `{e}`'
    st.session_state['health_chat'].append(('assistant', reply))

# --------------------------------------------------------------- results
result = st.session_state.get('result')
if result:
  profile = st.session_state['profile']
  st.divider()
  st.header(f"Results for {profile['name']}")
  counts = result['counts']
  m = st.columns(5)
  bmi = result.get('bmi')
  m[0].metric('BMI', bmi['bmi'] if bmi else '–', bmi['category'] if bmi else None, delta_color='off')
  m[1].metric('In range', counts['normal'])
  m[2].metric('Borderline', counts['borderline'])
  m[3].metric('Low / High', counts['low'] + counts['high'])
  m[4].metric('Very high', counts['very high'])
  if result.get('derived'):
    d = result['derived']
    names = {
        'non_hdl_cholesterol': 'Non-HDL cholesterol (mg/dL)',
        'total_chol_to_hdl_ratio': 'Total chol / HDL',
        'triglyceride_to_hdl_ratio': 'Triglyceride / HDL',
        'ast_to_alt_ratio': 'AST / ALT',
    }
    st.caption(' · '.join(f'{names[k]}: **{v:g}**' for k, v in d.items()))

  _cards(result['findings'])

  st.subheader('Recommendations')
  for role, text in st.session_state['health_chat']:
    with st.chat_message(role):
      st.markdown(text)
  follow = st.chat_input('Ask a follow-up (e.g. "Give me a 7-day meal plan for my cholesterol")')
  if follow:
    st.session_state['health_chat'].append(('user', follow))
    with st.chat_message('user'):
      st.markdown(follow)
    with st.chat_message('assistant'):
      with st.spinner('Thinking…'):
        try:
          reply = _ask(follow)
        except Exception as e:
          reply = f'⚠️ Could not reach the model: `{e}`'
      st.markdown(reply)
    st.session_state['health_chat'].append(('assistant', reply))
  st.caption('Disclaimer: This information is for informational purposes only and is not a substitute for professional medical advice, diagnosis, or treatment. Please seek advice from a qualified healthcare professional.')

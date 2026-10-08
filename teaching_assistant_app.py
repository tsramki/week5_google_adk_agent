"""Streamlit UI for the teaching assistant.

Run:  .venv/bin/streamlit run teaching_assistant_app.py
"""

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'teaching_assistant', '.env'))

from google.adk.runners import InMemoryRunner  # noqa: E402

from teaching_assistant.agent import root_agent  # noqa: E402
from ui_common import ask, set_page_config  # noqa: E402

APP_NAME = 'teaching_assistant'
SESSION_KEY = 'teach_adk_session'
CHAT_KEY = 'teach_chat'

set_page_config(page_title='Teaching Assistant', page_icon='🎓', layout='wide')
st.markdown('<style>.block-container {max-width: 1000px; padding-top: 2rem;}</style>',
            unsafe_allow_html=True)


@st.cache_resource
def _runner() -> InMemoryRunner:
  return InMemoryRunner(agent=root_agent, app_name=APP_NAME)


def _ask(prompt: str) -> str:
  try:
    return ask(_runner(), APP_NAME, SESSION_KEY, prompt)
  except Exception as e:  # surface credential/model errors in the UI
    return f'⚠️ Could not reach the model: `{e}`'


st.title('🎓 Teaching Assistant')
st.caption('Name a skill and get a researched, personalized learning plan with real resources.')

with st.form('teach_form'):
  skill = st.text_input('What do you want to learn?', placeholder='e.g. guitar, Python, watercolor, data analysis')
  c1, c2, c3 = st.columns(3)
  level = c1.selectbox('Current level', ['Complete beginner', 'Some experience', 'Intermediate', 'Advanced'])
  hours = c2.number_input('Hours per week', 1, 60, value=5)
  goal = c3.text_input('Goal or deadline (optional)', placeholder='e.g. play 3 songs in 3 months')
  submitted = st.form_submit_button('Create my learning plan', type='primary', use_container_width=True)

if submitted:
  if not skill.strip():
    st.error('Please tell me what you want to learn.')
  else:
    st.session_state[SESSION_KEY] = None
    with st.spinner('Researching resources and building your plan…'):
      reply = _ask(
          f'I want to learn: {skill.strip()}\nCurrent level: {level}\n'
          f'Time available: {hours} hours per week\nGoal/deadline: {goal.strip() or "none"}\n'
          'Please make me a plan.'
      )
    st.session_state[CHAT_KEY] = [('assistant', reply)]

if st.session_state.get(CHAT_KEY):
  st.divider()
  for role, text in st.session_state[CHAT_KEY]:
    with st.chat_message(role):
      st.markdown(text)
  follow = st.chat_input('Ask a follow-up (e.g. "make it 3 hours a week" or "add free resources only")')
  if follow:
    st.session_state[CHAT_KEY].append(('user', follow))
    with st.chat_message('user'):
      st.markdown(follow)
    with st.chat_message('assistant'):
      with st.spinner('Thinking…'):
        reply = _ask(follow)
      st.markdown(reply)
    st.session_state[CHAT_KEY].append(('assistant', reply))

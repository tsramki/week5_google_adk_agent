"""One launcher for all the agent front ends, with a project selector in the sidebar.

Run:  .venv/bin/streamlit run hub.py

Set APP_PASSWORD to require a password. On Cloud Run (K_SERVICE is set) the app
refuses to serve without one.
"""

import hmac
import os

import streamlit as st

st.set_page_config(page_title='Agent Hub', page_icon='🧭', layout='wide')

PASSWORD = os.environ.get('APP_PASSWORD')


def _require_login() -> None:
  if not PASSWORD:
    if os.environ.get('K_SERVICE'):
      st.error('APP_PASSWORD is not configured; refusing to serve.')
      st.stop()
    return  # local development without a password
  if st.session_state.get('authed'):
    return
  st.title('🧭 Agent Hub')
  with st.form('login'):
    entered = st.text_input('Password', type='password')
    if st.form_submit_button('Sign in', type='primary'):
      # Constant-time comparison.
      if hmac.compare_digest(entered.encode(), PASSWORD.encode()):
        st.session_state['authed'] = True
        st.rerun()
      st.error('Incorrect password.')
  st.stop()


_require_login()

pages = [
    st.Page('teaching_assistant_app.py', title='Teaching Assistant', icon='🎓', url_path='teaching', default=True),
    st.Page('app.py', title='Health Assistant', icon='🩺', url_path='health'),
    st.Page('financial_planner_app.py', title='Financial Planner', icon='💼', url_path='financial'),
]
st.navigation(pages).run()

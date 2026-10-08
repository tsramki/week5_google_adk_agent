"""Helpers shared by the Streamlit front ends."""

import asyncio
import uuid

import streamlit as st
from google.adk.runners import InMemoryRunner
from google.genai import types

USER_ID = 'streamlit_user'


def set_page_config(**kwargs) -> None:
  """No-op when the hub (hub.py) already configured the page."""
  try:
    st.set_page_config(**kwargs)
  except st.errors.StreamlitAPIException:
    pass


def ask(runner: InMemoryRunner, app_name: str, session_key: str, prompt: str) -> str:
  """Send one user turn to the agent and return its final text.

  The ADK session id is kept in st.session_state[session_key]; set it to None
  to start a fresh conversation.
  """

  async def go() -> str:
    sid = st.session_state.get(session_key)
    if sid is None:
      sid = uuid.uuid4().hex
      await runner.session_service.create_session(
          app_name=app_name, user_id=USER_ID, session_id=sid
      )
      st.session_state[session_key] = sid
    parts: list[str] = []
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=sid,
        new_message=types.Content(role='user', parts=[types.Part(text=prompt)]),
    ):
      if event.is_final_response() and event.content and event.content.parts:
        parts += [p.text for p in event.content.parts if p.text]
    return '\n'.join(parts) or '_(no response)_'

  return asyncio.run(go())

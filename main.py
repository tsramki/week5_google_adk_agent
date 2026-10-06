"""ADK web server for the teaching assistant, protected by HTTP Basic auth."""

import base64
import binascii
import hmac
import os

import uvicorn
from google.adk.cli.fast_api import get_fast_api_app

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
USERNAME = os.environ.get('APP_USERNAME', 'student')
PASSWORD = os.environ['APP_PASSWORD']


def _authorized(headers: list[tuple[bytes, bytes]]) -> bool:
  for name, value in headers:
    if name == b'authorization' and value[:6].lower() == b'basic ':
      try:
        user, _, password = (
            base64.b64decode(value[6:]).decode('utf-8').partition(':')
        )
      except (binascii.Error, UnicodeDecodeError):
        return False
      # Compare both fields to avoid leaking which one was wrong via timing.
      user_ok = hmac.compare_digest(user.encode(), USERNAME.encode())
      pass_ok = hmac.compare_digest(password.encode(), PASSWORD.encode())
      return user_ok and pass_ok
  return False


class BasicAuthMiddleware:
  """Pure ASGI middleware, so streaming (SSE) responses are not buffered."""

  def __init__(self, app):
    self.app = app

  async def __call__(self, scope, receive, send):
    if scope['type'] not in ('http', 'websocket') or _authorized(
        scope['headers']
    ):
      await self.app(scope, receive, send)
      return
    if scope['type'] == 'websocket':
      await send({'type': 'websocket.close', 'code': 1008})
      return
    await send({
        'type': 'http.response.start',
        'status': 401,
        'headers': [
            (b'www-authenticate', b'Basic realm="Teaching Assistant"'),
            (b'content-type', b'text/plain; charset=utf-8'),
        ],
    })
    await send({'type': 'http.response.body', 'body': b'Authentication required'})


app = get_fast_api_app(agents_dir=AGENTS_DIR, web=True)
app.add_middleware(BasicAuthMiddleware)

if __name__ == '__main__':
  uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

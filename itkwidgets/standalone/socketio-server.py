from pathlib import Path
from aiohttp import web
import socketio

from itkwidgets.standalone.config import WS_PORT

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

this_dir = Path(__file__).resolve().parent

async def index(request):
    """Serve the client-side application."""
    print(request)
    with open(this_dir / 'index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')

@sio.event
def connect(sid, environ):
    print("connect ", sid)

@sio.event
async def chat_message(sid, data):
    print("message ", data)

@sio.event
def disconnect(sid):
    print('disconnect ', sid)

app.router.add_static('/static', this_dir / 'static')
app.router.add_get('/', index)

if __name__ == '__main__':
    web.run_app(app, port=WS_PORT)

# import os
# import subprocess
# import sys
# import time
# import uuid

# import requests
# from requests import RequestException

# WS_PORT = 37480
# WS_SERVER_URL = f"http://127.0.0.1:{WS_PORT}"


# JWT_SECRET = str(uuid.uuid4())
# os.environ["JWT_SECRET"] = JWT_SECRET
# test_env = os.environ.copy()


# def socketio_server():
#     """Start server as test fixture and tear down after test."""
#     with subprocess.Popen(
#         [sys.executable, "-m", "hypha.server", f"--port={WS_PORT}"],
#         env=test_env,
#     ) as proc:

#         timeout = 10
#         while timeout > 0:
#             try:
#                 response = requests.get(f"http://127.0.0.1:{WS_PORT}/health/liveness")
#                 if response.ok:
#                     break
#             except RequestException:
#                 pass
#             timeout -= 0.1
#             time.sleep(0.1)
#         yield
#         proc.kill()
#         proc.terminate()

# from imjoy_rpc import connect_to_server, api

# if __name__ == '__main__':
#     # socketio_server()
#     fut = connect_to_server()

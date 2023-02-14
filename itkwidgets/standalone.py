import argparse
import asyncio
import functools
import socketio
import subprocess
import sys
import webbrowser

from aiohttp import web
from imjoy_rpc.hypha import connect_to_server
from itkwidgets.standalone.config import HYPHA_SERVER_URL, WS_SERVER_URL, WS_PORT
from pathlib import Path


sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)
server = None

this_dir = Path(__file__).resolve().parent

async def index(request):
    '''Serve the client-side application.'''
    with open(this_dir / 'standalone' / 'index.html') as f:
        return web.Response(body=server, text=f.read(), content_type='text/html')

app.router.add_get('/', index)

def start_hypha_server():
    subprocess.run([sys.executable, "-m", "hypha.server"], capture_output=True)

async def start_server(server_url, data, app):
    await connect_to_server({
        'client_id': 'py-itkwidgets-server',
        'name': 'py-itk-vtk-viewer-server',
        'server_url': server_url,
    })
    webbrowser.open_new_tab(WS_SERVER_URL)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--data', type=str, help='path to a data file')
    parser.add_argument('--type', type=str, help='Type of data (image, label_image, point_set)')
    opt = parser.parse_args()

    start_hypha_server()
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    app.on_startup.append(functools.partial(start_server, HYPHA_SERVER_URL, opt))
    web.run_app(app, port=WS_PORT, loop=loop)

import argparse
import asyncio
import code
import functools

import numpy as np

import imjoy
import itk
import socketio
import webbrowser

from aiohttp import web
from imjoy_rpc.hypha import connect_to_server
from itkwidgets.standalone.config import HYPHA_SERVER_URL, WS_SERVER_URL, WS_PORT
from itkwidgets.imjoy import register_itkwasm_imjoy_codecs_cli
from itkwidgets.viewer import view
from pathlib import Path
from urllib.parse import urlencode


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


async def start_server(server_url, data, app):
    server = await connect_to_server({
        'client_id': 'itkwidgets-server',
        'name': 'itkwidgets_server',
        'server_url': server_url,
    })
    imjoy.api.update(server)
    register_itkwasm_imjoy_codecs_cli(server)
    token = await server.generate_token()
    params = urlencode({'workspace': server.config.workspace, 'token': token, 'data': data.data})
    webbrowser.open_new_tab(f'{WS_SERVER_URL}/?{params}')
    loop.create_task(poll_for_services(server, data))

async def poll_for_services(server, data):
    while True:
        summary = await server.get_summary()
        names = [s["name"] for s in summary["services"]]
        if "itkwidgets_client" in names:
            # plugin has been exported
            break
    image = itk.imread(data.data)
    # number_of_points = 3000
    # gaussian_mean = [0.0, 0.0, 0.0]
    # gaussian_cov = [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 0.5]]
    # point_set = np.random.multivariate_normal(gaussian_mean, gaussian_cov, number_of_points)
    viewer = view(image)
    # loop.create_task(poll_for_viewer(viewer))

# async def poll_for_viewer(viewer):
#     while True:
#         await asyncio.sleep(2)
#         if viewer.has_viewer:
#             break
#     code.interact(local=locals())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--data', type=str, help='path to a data file')
    parser.add_argument('--type', type=str, help='Type of data (image, label_image, point_set)')
    opt = parser.parse_args()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    app.on_startup.append(functools.partial(start_server, HYPHA_SERVER_URL, opt))
    web.run_app(app, port=WS_PORT, loop=loop)

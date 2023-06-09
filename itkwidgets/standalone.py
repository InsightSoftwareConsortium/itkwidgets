import argparse
import asyncio
import code
import uuid
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

import requests
from requests import RequestException
import webbrowser

import imjoy_rpc
import itk

from imjoy_rpc.hypha import connect_to_server
from itkwidgets.standalone.config import SERVER_HOST, SERVER_PORT, VIEWER_HTML
from itkwidgets.imjoy import register_itkwasm_imjoy_codecs_cli
from itkwidgets.viewer import view, Viewer
from pathlib import Path
from urllib.parse import urlencode

async def test_numpy_array(socketio_server):
    """Test numpy array."""
    ws = await connect_to_server(
        {"client_id": "test-plugin", "server_url": WS_SERVER_URL}
    )
    await ws.export(ImJoyPlugin(ws))
    workspace = ws.config.workspace
    token = await ws.generate_token()

    api = await connect_to_server(
        {
            "client_id": "client",
            "workspace": workspace,
            "token": token,
            "server_url": WS_SERVER_URL,
        }
    )
    plugin = await api.get_service("test-plugin:default")
    result = await plugin.add(2.1)
    assert result == 2.1 + 1.0

    large_array = np.zeros([2048, 2048, 4], dtype="float32")
    result = await plugin.add(large_array)
    np.testing.assert_array_equal(result, large_array + 1.0)

async def start_viewer(server_url, viewer_opts):
    data = viewer_opts.data

    server = await connect_to_server({
        'client_id': 'itkwidgets-server',
        'name': 'itkwidgets_server',
        'server_url': server_url,
    })
    imjoy_rpc.api.update(server)
    register_itkwasm_imjoy_codecs_cli(server)
    token = await server.generate_token()
    # params = urlencode({'workspace': server.config.workspace, 'token': token, 'data': data})
    params = urlencode({'workspace': server.config.workspace, 'token': token})
    webbrowser.open_new_tab(f'{server_url}/itkwidgets/index.html?{params}')

    # Needed?
    await poll_for_services(server)
    print('services found')

    image = itk.imread(data)
    # number_of_points = 3000
    # gaussian_mean = [0.0, 0.0, 0.0]
    # gaussian_cov = [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 0.5]]
    # point_set = np.random.multivariate_normal(gaussian_mean, gaussian_cov, number_of_points)
    # viewer = view(image)
    # print(viewer)
    viewer = Viewer()
    print(viewer)
    await poll_for_viewer(viewer)

    # viewer.set_image(image)
    await viewer.set_image_async(image)
    # time.sleep(30)
    await asyncio.sleep(30)
    # await poll_for_viewer(viewer)
    # loop.create_task(poll_for_viewer(viewer))

async def poll_for_services(server):
    while True:
        summary = await server.get_summary()
        names = [s["name"] for s in summary["services"]]
        if "itkwidgets_client" in names:
            # plugin has been exported
            break

async def poll_for_viewer(viewer):
    while True:
        await asyncio.sleep(2)
        if viewer.has_viewer:
            break
    # code.interact(local=locals())

def main(viewer_opts):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    JWT_SECRET = str(uuid.uuid4())
    os.environ["JWT_SECRET"] = JWT_SECRET
    hypha_server_env = os.environ.copy()

    server_url = f"http://{SERVER_HOST}:{SERVER_PORT}"
    viewer_mount_dir = str(Path(VIEWER_HTML).parent)

    with subprocess.Popen(
        [sys.executable, "-m", "hypha.server", f"--host={SERVER_HOST}",
         f"--port={SERVER_PORT}", "--static-mounts",
         f"/itkwidgets:{viewer_mount_dir}"],
        env=hypha_server_env,
    ) as proc:

        timeout = 10
        while timeout > 0:
            try:
                response = requests.get(f"{server_url}/health/liveness")
                if response.ok:
                    break
            except RequestException:
                pass
            timeout -= 0.1
            time.sleep(0.1)

        # loop.run_until_complete(start_viewer(server_url, viewer_opts))
        loop.create_task(start_viewer(server_url, viewer_opts))
        loop.run_forever()
        time.sleep(30)
        loop.close()

        proc.kill()
        proc.terminate()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--data', type=str, help='path to a data file')
    parser.add_argument('--type', type=str, help='Type of data (image, label_image, point_set)')
    opts = parser.parse_args()

    main(opts)

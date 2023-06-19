import argparse
import asyncio
import uuid
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from requests import RequestException
import webbrowser

import imjoy_rpc
import itk

from imjoy_rpc.hypha import connect_to_server
from itkwidgets.standalone.config import SERVER_HOST, SERVER_PORT, VIEWER_HTML
from itkwidgets.imjoy import register_itkwasm_imjoy_codecs_cli
from itkwidgets._initialization_params import build_config, build_init_data
from pathlib import Path
from urllib.parse import urlencode


def _snake_to_camel(variable):
    first, *words = variable.split('_')
    return first + ''.join([w.capitalize() for w in words])


def input_dict():
    user_input = vars(opts)
    if opts.image:
        image = itk.imread(opts.image)
        user_input['image'] = image
    if opts.label_image:
        label_image = itk.imread(opts.label_image)
        user_input['label_image'] = label_image

    data = build_init_data(user_input)
    data = {_snake_to_camel(k):v for k, v in data.items()}
    ui = user_input.get('ui', "reference")
    data['config'] = build_config(ui)

    return { 'data': data }


async def start_viewer(server_url):
    server = await connect_to_server({
        'client_id': 'itkwidgets-server',
        'name': 'itkwidgets_server',
        'server_url': server_url,
    })
    imjoy_rpc.api.update(server)
    register_itkwasm_imjoy_codecs_cli(server)

    await server.register_service({
        "name": "itkwidgets_input_obj",
        "id": "itkwidgets-input-obj",
        "description":
            "Provide the data and config object required to create a viewer.",
        "config": {
            "visibility": "protected",
            "require_context": False,
            "run_in_executor": False,
        },
        "inputObject": input_dict
    })

    workspace = server.config.workspace
    token = await server.generate_token()
    params = urlencode({'workspace': workspace, 'token': token})
    webbrowser.open_new_tab(f'{server_url}/itkwidgets/index.html?{params}')


def main():
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

        loop.create_task(start_viewer(server_url))
        loop.run_forever()
        time.sleep(30)
        loop.close()

        proc.kill()
        proc.terminate()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--image', type=str, help='path to an image data file')
    parser.add_argument('--label-image', type=str, help='path to a label image data file')
    parser.add_argument('--point-set', type=str, help='path to a point set data file')
    parser.add_argument('--use2D', dest='use2D', action='store_true', default=False, help='Image is 2D')
    parser.add_argument('--rotate', dest='rotate', action='store_true', default=False, help='initialize viewer with rotating image')
    parser.add_argument('--ui', type=str, choices=['reference', 'pydata-sphinx'], default='reference', help='Which UI to use')
    parser.add_argument('--gradient-opacity', type=float, help='Set the gradient opacity in the volume rendering. Values range from 0.0 to 1.0.')
    opts = parser.parse_args()

    main(opts)

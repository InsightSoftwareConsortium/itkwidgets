import argparse
import logging
import socket
import uuid
import os
import subprocess
import sys
import time
from pathlib import Path

import webbrowser

import imjoy_rpc

from imjoy_rpc.hypha import connect_to_server, connect_to_server_sync
from itkwidgets.standalone.config import SERVER_HOST, SERVER_PORT, VIEWER_HTML
from itkwidgets.imjoy import register_itkwasm_imjoy_codecs_cli
from itkwidgets._initialization_params import (
    build_config,
    build_init_data,
    init_params_dict,
    INPUT_OPTIONS,
)
from itkwidgets.viewer import Viewer
from ngff_zarr import detect_cli_io_backend, cli_input_to_ngff_image, ConversionBackend
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib3 import PoolManager, exceptions

logging.getLogger("urllib3").setLevel(logging.ERROR)

def find_port(port=SERVER_PORT):
    # Find first available port starting at SERVER_PORT
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex((SERVER_HOST, port)) == 0:
            # Port in use, try again
            return find_port(port=port + 1)
        else:
            return port


PORT = find_port()
OPTS = None


def standalone_viewer(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    server_url = f"http://{SERVER_HOST}:{parsed.port}"
    workspace = query.get("workspace", [""])[0]
    token = query.get("token", [""])[0]

    server = connect_to_server_sync(
        {"server_url": server_url, "workspace": workspace, "token": token}
    )
    imjoy_rpc.api.update(server.server)
    register_itkwasm_imjoy_codecs_cli(server.server)

    svc = server.get_service(f"{workspace}/itkwidgets-client:itk-vtk-viewer")
    return Viewer(itk_viewer=svc.viewer())


def input_dict():
    user_input = read_files()
    data = build_init_data(user_input)
    ui = user_input.get("ui", "reference")
    data["config"] = build_config(ui)
    return {"data": data}


def read_files():
    user_input = vars(OPTS)
    reader = user_input.get("reader", None)
    for param in INPUT_OPTIONS:
        input = user_input.get(param, None)
        if input:
            if reader:
                reader = ConversionBackend(reader)
            else:
                reader = detect_cli_io_backend(input)
            ngff_image = cli_input_to_ngff_image(reader, [input])
            user_input[param] = ngff_image
    return user_input


async def viewer_ready(itk_viewer):
    init_viewer_kwargs = vars(OPTS)
    settings = init_params_dict(itk_viewer)
    for key, value in init_viewer_kwargs.items():
        if key in settings.keys() and value is not None:
            settings[key](value)


def start_viewer(server_url):
    server = connect_to_server_sync(
        {
            "client_id": "itkwidgets-server",
            "name": "itkwidgets_server",
            "server_url": server_url,
        }
    )
    register_itkwasm_imjoy_codecs_cli(server)

    server.register_service(
        {
            "name": "itkwidgets_input_obj",
            "id": "itkwidgets-input-obj",
            "description": "Provide the data and config object required to create a viewer.",
            "config": {
                "visibility": "protected",
                "require_context": False,
                "run_in_executor": True,
            },
            "inputObject": input_dict,
        }
    )

    server.register_service(
        {
            "name": "itkwidgets_viewer_ready",
            "id": "itkwidgets-viewer-ready",
            "description": "",
            "config": {
                "visibility": "protected",
                "require_context": False,
                "run_in_executor": True,
            },
            "viewerReady": viewer_ready,
        }
    )

    workspace = server.config.workspace
    token = server.generate_token()
    params = urlencode({"workspace": workspace, "token": token})
    webbrowser.open_new_tab(f"{server_url}/itkwidgets/index.html?{params}")


def main():
    JWT_SECRET = str(uuid.uuid4())
    os.environ["JWT_SECRET"] = JWT_SECRET
    hypha_server_env = os.environ.copy()

    server_url = f"http://{SERVER_HOST}:{PORT}"
    viewer_mount_dir = str(Path(VIEWER_HTML).parent)

    out = None if OPTS.verbose else subprocess.DEVNULL
    err = None if OPTS.verbose else subprocess.STDOUT
    with subprocess.Popen(
        [
            sys.executable,
            "-m",
            "hypha.server",
            f"--host={SERVER_HOST}",
            f"--port={PORT}",
            "--static-mounts",
            f"/itkwidgets:{viewer_mount_dir}",
        ],
        env=hypha_server_env,
        stdout=out,
        stderr=err,
    ):
        timeout = 10
        while timeout > 0:
            try:
                http = PoolManager()
                response = http.request("GET", f"{server_url}/health/liveness")
                if response.status == 200:
                    break
            except exceptions.MaxRetryError:
                pass
            timeout -= 0.1
            time.sleep(0.1)

        start_viewer(server_url)


def cli_entrypoint():
    global OPTS

    parser = argparse.ArgumentParser()

    parser.add_argument("data", nargs="?", type=str, help="Path to a data file.")
    parser.add_argument("--image", type=str, help="Path to an image data file.")
    parser.add_argument(
        "--label-image", type=str, help="Path to a label image data file."
    )
    parser.add_argument("--point-set", type=str, help="Path to a point set data file.")
    parser.add_argument(
        "--use2D", dest="use2D", action="store_true", default=False, help="Image is 2D."
    )
    parser.add_argument(
        "--reader",
        type=str,
        choices=["ngff_zarr", "zarr", "itk", "tifffile", "imageio"],
        help="Backend to use to read the data file(s). Optional.",
    )
    parser.add_argument(
        "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="Print all log messages to stdout.",
    )
    # General Interface
    parser.add_argument(
        "--rotate",
        dest="rotate",
        action="store_true",
        default=False,
        help="Continuously rotate the camera around the scene in volume rendering mode.",
    )
    parser.add_argument(
        "--ui",
        type=str,
        choices=["reference", "pydata-sphinx"],
        default="reference",
        help="Which UI to use",
    )
    parser.add_argument(
        "--ui-collapsed",
        dest="ui_collapsed",
        action="store_true",
        default=False,
        help="Collapse the native widget user interface.",
    )
    parser.add_argument(
        "--no-annotations",
        dest="annotations",
        action="store_false",
        default=True,
        help="Display annotations describing orientation and the value of a mouse-position-based data probe.",
    )
    parser.add_argument(
        "--axes", dest="axes", action="store_true", default=False, help="Display axes."
    )
    parser.add_argument(
        "--bg-color",
        type=tuple,
        nargs="+",
        help="Background color: (red, green, blue) tuple, components from 0.0 to 1.0.",
    )
    # Images
    parser.add_argument(
        "--label-blend",
        type=float,
        help="Label map blend with intensity image, from 0.0 to 1.0.",
    )
    parser.add_argument(
        "--label-names",
        type=list,
        nargs="+",
        help="String names associated with the integer label values. List of (label_value, label_name).",
    )
    parser.add_argument(
        "--label-lut",
        type=str,
        help="Lookup table for the label map.",
    )
    parser.add_argument(
        "--label-weights",
        type=float,
        help="The rendering weight assigned to current label. Values range from 0.0 to 1.0.",
    )
    parser.add_argument(
        "--color-range",
        type=list,
        nargs="+",
        help="The [min, max] range of intensity values mapped to colors for the given image component identified by name.",
    )
    parser.add_argument(
        "--color-bounds",
        type=list,
        nargs="+",
        help="The [min, max] range of intensity values for color maps that provide a bounds for user inputs.",
    )
    parser.add_argument(
        "--cmap",
        type=str,
        help="The color map for the current component/channel.",
    )
    parser.add_argument(
        "--x-slice",
        type=float,
        help="The position in world space of the X slicing plane.",
    )
    parser.add_argument(
        "--y-slice",
        type=float,
        help="The position in world space of the Y slicing plane.",
    )
    parser.add_argument(
        "--z-slice",
        type=float,
        help="The position in world space of the Z slicing plane.",
    )
    parser.add_argument(
        "--no-interpolation",
        dest="interpolation",
        action="store_false",
        default=True,
        help="Linear as opposed to nearest neighbor interpolation for image slices.",
    )
    parser.add_argument(
        "--gradient-opacity",
        type=float,
        help="Gradient opacity for composite volume rendering, in the range (0.0, 1.0].",
    )
    parser.add_argument(
        "--gradient-opacity-scale",
        type=float,
        help="Gradient opacity scale for composite volume rendering, in the range (0.0, 1.0].",
    )
    parser.add_argument(
        "--blend-mode",
        type=str,
        help='Volume rendering blend mode. Supported modes: "Composite", "Maximum", "Minimum", "Average".',
    )
    parser.add_argument(
        "--component-hidden",
        dest="component_visible",
        action="store_false",
        default=True,
        help="Whether to used gradient-based shadows in the volume rendering.",
    )
    parser.add_argument(
        "--shadow-disabled",
        dest="shadow_enabled",
        action="store_false",
        default=True,
        help="Whether to used gradient-based shadows in the volume rendering.",
    )
    parser.add_argument(
        "--view-mode",
        type=str,
        choices=["XPlane", "YPlane", "ZPlane", "Volume"],
        help="Only relevant for 3D scenes.",
    )
    parser.add_argument(
        "--layer",
        type=str,
        help="Select the layer identified by `name` in the user interface.",
    )
    parser.add_argument(
        "--layer-hidden",
        dest="layer_visible",
        action="store_false",
        default=True,
        help="Whether the current layer is visible.",
    )
    # Other Parameters
    parser.add_argument(
        "--sample-distance",
        type=float,
        help="Sampling distance for volume rendering, normalized from 0.0 to 1.0. Lower values result in a higher quality rendering. High values improve the framerate.",
    )
    parser.add_argument("--units", type=str, help="Units to display in the scale bar.")

    OPTS = parser.parse_args()

    main()

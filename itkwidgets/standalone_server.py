import argparse
import functools
import logging
import socket
import code
import threading
import uuid
import os
import subprocess
import sys
import time
from pathlib import Path
from base64 import b64decode
import webbrowser

import imjoy_rpc

from imjoy_rpc.hypha import connect_to_server_sync
from itkwidgets.standalone.config import SERVER_HOST, SERVER_PORT, VIEWER_HTML
from itkwidgets.imjoy import register_itkwasm_imjoy_codecs_cli
from itkwidgets._initialization_params import (
    build_config,
    build_init_data,
    init_params_dict,
    DATA_OPTIONS,
)
from itkwidgets.viewer import view
from ngff_zarr import detect_cli_io_backend, cli_input_to_ngff_image, ConversionBackend
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib3 import PoolManager, exceptions

logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("websocket-client").setLevel(logging.ERROR)


def find_port(port=SERVER_PORT):
    # Find first available port starting at SERVER_PORT
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex((SERVER_HOST, port)) == 0:
            # Port in use, try again
            return find_port(port=port + 1)
        else:
            return port


VIEWER = None
BROWSER = None


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
    return view(itk_viewer=svc.viewer())


def input_dict(viewer_options):
    user_input = read_files(viewer_options)
    data = build_init_data(user_input)
    ui = user_input.get("ui", "reference")
    data["config"] = build_config(ui)

    if data["view_mode"] is not None:
        vm = data["view_mode"]
        if vm == "x":
            data["view_mode"] = "XPlane"
        elif vm == "y":
            data["view_mode"] = "YPlane"
        elif vm == "z":
            data["view_mode"] = "ZPlane"
        elif vm == "v":
            data["view_mode"] = "Volume"

    return {"data": data}


def read_files(viewer_options):
    user_input = vars(viewer_options)
    reader = user_input.get("reader", None)
    for param in DATA_OPTIONS:
        input = user_input.get(param, None)
        if input:
            if reader:
                reader = ConversionBackend(reader)
            else:
                reader = detect_cli_io_backend([input])
            if not input.find('://') == -1 and not Path(input).exists():
                sys.stderr.write(f"File not found: {input}\n")
                # hack
                raise KeyboardInterrupt
            ngff_image = cli_input_to_ngff_image(reader, [input])
            user_input[param] = ngff_image
    return user_input


class ViewerReady:
    def __init__(self, viewer_options, init_params_dict):
        self.init_viewer_kwargs = vars(viewer_options)
        self.init_params_dict = init_params_dict
        self.event = threading.Event()

    async def on_ready(self, itk_viewer):
        settings = self.init_params_dict(itk_viewer)
        for key, value in self.init_viewer_kwargs.items():
            if key in settings.keys() and value is not None:
                settings[key](value)

        self.event.set()

    def wait(self):
        self.event.wait()


def set_label_or_image(server, type):
    workspace = server.config.workspace
    svc = server.get_service(f"{workspace}/itkwidgets-client:set-label-or-image")
    getattr(svc, f"set_{type}")()


def fetch_zarr_store(store_type):
    return getattr(VIEWER, store_type, None)


def start_viewer(server_url, viewer_options):
    server = connect_to_server_sync(
        {
            "client_id": "itkwidgets-server",
            "name": "itkwidgets_server",
            "server_url": server_url,
        }
    )
    register_itkwasm_imjoy_codecs_cli(server)

    input_obj = input_dict(viewer_options)
    viewer_ready = ViewerReady(viewer_options, init_params_dict)
    server.register_service(
        {
            "name": "parsed_data",
            "id": "parsed-data",
            "description": "Provide parsed data to the client.",
            "config": {
                "visibility": "protected",
                "require_context": False,
                "run_in_executor": True,
            },
            "inputObject": lambda: input_obj,
            "viewerReady": viewer_ready.on_ready,
            "fetchZarrStore": fetch_zarr_store,
        }
    )

    server.register_service(
        {
            "name": "data_set",
            "id": "data-set",
            "description": "Save the image data set via REPL session.",
            "config": {
                "visibility": "protected",
                "require_context": False,
                "run_in_executor": True,
            },
            "set_label_or_image": functools.partial(set_label_or_image, server),
        }
    )

    return server, input_obj, viewer_ready


def main(viewer_options):
    global VIEWER
    JWT_SECRET = str(uuid.uuid4())
    os.environ["JWT_SECRET"] = JWT_SECRET
    hypha_server_env = os.environ.copy()

    port = find_port()
    server_url = f"http://{SERVER_HOST}:{port}"
    viewer_mount_dir = str(Path(VIEWER_HTML).parent)

    out = None if viewer_options.verbose else subprocess.DEVNULL
    err = None if viewer_options.verbose else subprocess.STDOUT
    with subprocess.Popen(
        [
            sys.executable,
            "-m",
            "hypha.server",
            f"--host={SERVER_HOST}",
            f"--port={port}",
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

        server, input_obj, viewer_ready = start_viewer(server_url, viewer_options)
        workspace = server.config.workspace
        token = server.generate_token()
        params = urlencode({"workspace": workspace, "token": token})
        url = f"{server_url}/itkwidgets/index.html?{params}"

        # Updates for resolution progression
        rate = 1.0
        fast_rate = 0.05
        if viewer_options.rotate:
            rate = fast_rate

        if viewer_options.browser:
            sys.stdout.write(f"Viewer url:\n\n  {url}\n\n")
            webbrowser.open_new_tab(f"{server_url}/itkwidgets/index.html?{params}")
        else:
            from playwright.sync_api import sync_playwright
            playwright = sync_playwright().start()
            args = [
                "--enable-unsafe-webgpu",
            ]
            browser = playwright.chromium.launch(args=args)
            BROWSER = browser
            page = browser.new_page()

            terminal_size = os.get_terminal_size()
            width = terminal_size.columns * 10
            is_tmux = 'TMUX' in os.environ and 'tmux' in os.environ['TMUX']
            # https://github.com/tmux/tmux/issues/1502
            if is_tmux:
                if viewer_options.use2D:
                    width = min(width, 320)
                else:
                    width = min(width, 420)
            else:
                width = min(width, 768)
            height = width
            page.set_viewport_size({"width": width, "height": height})

            response = page.goto(url, timeout=0, wait_until="load")
            assert response.status == 200, (
                "Failed to start browser app instance, "
                f"status: {response.status}, url: {url}"
            )

            input_data = input_obj["data"]
            if not input_data["use2D"]:
                if input_data["x_slice"] is None and input_data["view_mode"] == "XPlane":
                    page.locator('label[itk-vtk-tooltip-content="X plane play scroll"]').click()
                    rate = fast_rate
                elif input_data["y_slice"] is None and input_data["view_mode"] == "YPlane":
                    page.locator('label[itk-vtk-tooltip-content="Y plane play scroll"]').click()
                    rate = fast_rate
                elif input_data["z_slice"] is None and input_data["view_mode"] == "ZPlane":
                    page.locator('label[itk-vtk-tooltip-content="Z plane play scroll"]').click()
                    rate = fast_rate

        viewer_ready.wait()  # Wait until viewer is created before launching REPL
        workspace = server.config.workspace
        svc = server.get_service(f"{workspace}/itkwidgets-client:itk-vtk-viewer")
        VIEWER = view(itk_viewer=svc.viewer(), server=server)
        if not viewer_options.browser:
            from imgcat import imgcat
            terminal_height = min(terminal_size.lines - 1, terminal_size.columns // 3)


            while True:
                png_bin = b64decode(svc.capture_screenshot()[22:])
                imgcat(png_bin, height=terminal_height)
                time.sleep(rate)
                CSI = b'\033['
                sys.stdout.buffer.write(CSI + str(terminal_height).encode() + b"F")

        if viewer_options.repl:
            banner = f"""
                Welcome to the itkwidgets command line tool! Press CTRL+D or
                run `exit()` to terminate the REPL session. Use the `viewer`
                object to manipulate the viewer.
            """
            exitmsg = "Exiting REPL. Press CTRL+C to exit the viewer."
            code.interact(banner=banner, local={"viewer": VIEWER, "svc": svc, "server": server}, exitmsg=exitmsg)


def cli_entrypoint():
    parser = argparse.ArgumentParser()

    parser.add_argument("data", nargs="?", type=str, help="Path to a data file.")
    parser.add_argument("-i", "--image", dest="image", type=str, help="Path to an image data file.")
    parser.add_argument(
        "-l", "--label-image", dest="label_image", type=str, help="Path to a label image data file."
    )
    parser.add_argument("-p", "--point-set", dest="point_set", type=str, help="Path to a point set data file.")
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
    parser.add_argument(
        "-b", "--browser",
        dest="browser",
        action="store_true",
        default=False,
        help="Render to a browser tab instead of the terminal.",
    )
    parser.add_argument(
        "--repl",
        dest="repl",
        action="store_true",
        default=False,
        help="Start interactive REPL after launching viewer.",
    )
    # General Interface
    parser.add_argument(
        "-r", "--rotate",
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
        default=(0.0, 0.0, 0.0),
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
        "-m", "--view-mode",
        type=str,
        choices=["x", "y", "z", "v"],
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

    viewer_options = parser.parse_args()

    try:
        main(viewer_options)
    except KeyboardInterrupt:
        if BROWSER:
            BROWSER.close()
        if not viewer_options.browser:
            # Clear `^C%`
            CSI = b'\033['
            sys.stdout.buffer.write(CSI + b"1K")
            sys.stdout.buffer.write(b"\n")
        sys.exit(0)


if __name__ == "__main__":
    cli_entrypoint()

import argparse
import asyncio
import subprocess
import sys


def start_hypha_server():
    subprocess.run([sys.executable, "-m", "hypha.server"], capture_output=True)

# async def main():
#     ws = await connect_to_server(config)
#     print(ws)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--data', type=str, help='path to a data file')
    parser.add_argument('--type', type=str, help='Type of data (image, label_image, point_set)')
    opt = parser.parse_args()

    start_hypha_server()

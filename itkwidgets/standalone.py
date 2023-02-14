import argparse
import asyncio

async def start_server(server_url):
    config = { 'server_url': server_url, 'workspace': 'viewer' }
    server = await connect_to_server(config)
    print(server)

# async def main():
#     ws = await connect_to_server(config)
#     print(ws)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--data', type=str, help='path to a data file')
    parser.add_argument('--type', type=str, help='Type of data (image, label_image, point_set)')
    opt = parser.parse_args()

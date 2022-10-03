from imjoy_rpc.hypha import connect_to_server
from itkwidgets.standalone.config import WS_SERVER_URL
import asyncio

async def start_server(server_url):
    config = { 'server_url': server_url, 'workspace': 'viewer' }
    server = await connect_to_server(config)
    print(server)

# async def main():
#     ws = await connect_to_server(config)
#     print(ws)

if __name__ == '__main__':
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # loop.run_until_complete(main())
    loop = asyncio.get_event_loop()
    loop.create_task(start_server(WS_SERVER_URL))
    loop.run_forever()
    # asyncio.run(main())

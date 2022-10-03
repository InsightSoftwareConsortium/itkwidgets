from imjoy_rpc.hypha import connect_to_server
from itkwidgets.standalone.config import WS_SERVER_URL
import asyncio

async def main():
    config = { 'server_url': 'http://127.0.0.1:9000' }
    ws = await connect_to_server(config)
    print(ws)

if __name__ == '__main__':
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # loop.run_until_complete(main())
    asyncio.run(main())

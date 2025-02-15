import asyncio

from config import TOKEN_D
from trad.connect_tinkoff import ConnectTinkoff
from trad.task_all_time import processing_stream_portfolio


async def main():
    connect = ConnectTinkoff(TOKEN_D)
    await connect.connect()
    await processing_stream_portfolio(connect, 1)


if __name__ == '__main__':
    asyncio.run(main())

import asyncio

from config import init_config
from market_maker import MarketMaker


async def run_market_maker(config, loop):
    market_maker = MarketMaker(config)
    await market_maker.run(loop)


if __name__ == '__main__':
    config = init_config()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_market_maker(config, loop))

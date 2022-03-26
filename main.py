from config import init_config
from market_maker import MarketMaker
from logger import get_logger

logger = get_logger("DexalotMM")

if __name__ == "__main__":

    config = init_config()

    dexalot_mm = MarketMaker(config)
    dexalot_mm.start()

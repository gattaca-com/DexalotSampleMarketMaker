class OrderStatus:
    REJECTED = 1
    PARTIAL = 2
    FILLED = 3
    CANCELLED = 4
    EXPIRED = 5
    KILLED = 6


class OrderSide:
    BUY = 0
    SELL = 1


class OrderType:
    MARKET = 0
    LIMIT = 1
    STOP = 2
    STOPLIMIT = 3
    LIMITFOK = 4

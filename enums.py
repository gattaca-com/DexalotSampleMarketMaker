from enum import Enum


class GTCEnum(Enum):

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return str(self.name)


class OrderStatus(GTCEnum):
    REJECTED = 1
    PARTIAL = 2
    FILLED = 3
    CANCELLED = 4
    EXPIRED = 5
    KILLED = 6


class OrderSide(GTCEnum):
    BUY = 0
    SELL = 1


class OrderType(GTCEnum):
    MARKET = 0
    LIMIT = 1
    STOP = 2
    STOPLIMIT = 3
    LIMITFOK = 4

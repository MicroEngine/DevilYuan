from DyCommon.DyCommon import *
from ..DyStockBackTestingCommon import *
from EventEngine.DyEventEngine import *

from .Strategy.DyStockBackTestingStrategyEngine import *


class DyStockBackTestingMainEngine(object):
    """ 股票回测主引擎 """

    def __init__(self):
        self._eventEngine = DyEventEngine(DyStockBackTestingEventHandType.nbr, False)
        self._info = DyInfo(self._eventEngine)

        self._strategyEngine = DyStockBackTestingStrategyEngine(self._eventEngine, self._info)

        self._eventEngine.start()

    @property
    def eventEngine(self):
        return self._eventEngine

    @property
    def info(self):
        return self._info

    def exit(self):
        pass

    def setThreadMode(self):
        self._strategyEngine.setThreadMode(threadMode)

    def setProcessMode(self, mode):
        self._strategyEngine.setProcessMode(mode)
from EventEngine.DyEventEngine import *
from .DyStockDataEngine import *
from ..DyStockDataCommon import *
from DyCommon.DyCommon import *


class DyStockDataMainEngine(object):
    """description of class"""

    def __init__(self):
        self._eventEngine = DyEventEngine(DyStockDataEventHandType.nbr, False)
        self._info = DyInfo(self._eventEngine)

        self._dataEngine = DyStockDataEngine(self._eventEngine, self._info)

        self._eventEngine.start()

    @property
    def eventEngine(self):
        return self._eventEngine

    @property
    def info(self):
        return self._info

    @property
    def dataEngine(self):
        return self._dataEngine

    def exit(self):
        pass
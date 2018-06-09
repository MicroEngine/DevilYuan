from DyCommon.DyCommon import *

class DyStockTradeLog(object):
    """description of class"""

    def __init__(self, eventEngine):
        self._eventEngine = eventEngine

    def print(self, description, type = DyLogData.info):
        event = DyEvent(DyEventType.log)
        event.data = DyLogData(description, type)

        self._eventEngine.put(event)
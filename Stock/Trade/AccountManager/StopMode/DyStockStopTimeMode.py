from .DyStockStopMode import *
from ...DyStockTradeCommon import *


class DyStockStopTimeMode(DyStockStopMode):

    profitRunningPnlRatio = 10

    def __init__(self, accountManager, dayNbr, pnlRatio):
        super().__init__(accountManager)

        self._dayNbr = dayNbr
        self._pnlRatio = pnlRatio

        self._tradeStartTime = '14:55:00'

    def onTicks(self, ticks):
        for code, pos in self._accountManager.curPos.items():
            tick = ticks.get(code)
            if tick is None:
                continue

            if pos.holdingPeriod >= self._dayNbr:
                if pos.pnlRatio >= self._pnlRatio:
                    self._accountManager.closePos(tick.datetime, code, getattr(tick, DyStockTradeCommon.sellPrice), DyStockSellReason.stopTime)

    def onBars(self, bars):
        self.onTicks(bars)

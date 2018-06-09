from .DyStockStopMode import *
from ...DyStockTradeCommon import *


class DyStockStopProfitMaMode(DyStockStopMode):
    
    profitRunningPnlRatio = 10

    def __init__(self, accountManager, dataEngine, ma):
        super().__init__(accountManager)

        self._dataEngine = dataEngine
        self._daysEngine = self._dataEngine.daysEngine
        self._ma = ma

        self._tradeStartTime = '14:55:00'

        self._curInit()

    def _curInit(self):
        self._preparedData = {}

    def onOpen(self, date):

        self._curInit()

        preDate = self._daysEngine.tDaysOffsetInDb(date, -1)

        for code in self._accountManager.curPos:
            if not self._daysEngine.loadCode(code, [preDate, -self._ma+2], latestAdjFactorInDb = False):
                return False

            df = self._daysEngine.getDataFrame(code)
            if df.shape[0] != (self._ma - 1): return False
            
            self._preparedData[code] = df['close'].values.tolist()

        return True

    def _processAdj(self, code, tick):
        """ 处理除复权 """

        if tick.preClose is None: return

        if code not in self._preparedData: return False
        if code not in self._accountManager.curPos: return False

        closes = self._preparedData[code]

        if tick.preClose == closes[-1]:
            return True

        # 复权
        adjFactor = tick.preClose/closes[-1]

        # 价格
        closes = list(map(lambda x,y:x*y, closes, [adjFactor]*len(closes)))
        closes[-1] = tick.preClose # 浮点数的精度问题

        self._preparedData[code] = closes

        return True

    def _stopProfit(self, code, tick):
        ma = (sum(self._preparedData[code]) + tick.price)/self._ma

        pos = self._accountManager.curPos[code]

        if pos.maxPnlRatio > self.profitRunningPnlRatio and tick.price < ma:
            self._accountManager.closePos(tick.datetime, code, getattr(tick, DyStockTradeCommon.sellPrice), DyStockSellReason.stopProfit)

    def onTicks(self, ticks):
        for code, pos in self._accountManager.curPos.items():
            tick = ticks.get(code)
            if tick is None:
                continue

            if tick.time < self._tradeStartTime:
                return

            if not self._processAdj(code, tick):
                continue

            self._stopProfit(code, tick)
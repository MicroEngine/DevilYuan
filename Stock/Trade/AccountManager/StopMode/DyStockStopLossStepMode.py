import math

from .DyStockStopMode import *
from ...DyStockTradeCommon import *


class DyStockStopLossStepMode(DyStockStopMode):
    
    def __init__(self, accountManager, initSLM=0.9, step=0.1, increment=0.09):
        """
            激活阶梯停损，可以不需要止盈模式，也就是说包含止盈和止损。

            https://www.ricequant.com/community/topic/1423/#share-source-code_content_7899_886349
            @initSLM=0.9    # 初始止损比例 M 
            @step=0.10      # 间隔 X, 阶梯长度
            @increment=0.09 # 止损增量 Y, 阶梯变化率（阶梯每改变一次， 止损线上涨的幅度）

            止损线改变次数 = floor[log(周期内最高股价/买入价)/log(1 + X%)]
            止损比例 = M * [1+Y%] ^ 止损线改变次数
            止损价 = 止损比例 * 成本价

            if 现价< 止损价： 
                直接跌破止损价， 卖出止损。
            else：
                继续持有
        """
        super().__init__(accountManager)

        self._initSLM = initSLM
        self._step = step
        self._increment = increment

    def onTicks(self, ticks):
        for code, pos in self._accountManager.curPos.items():
            tick = ticks.get(code)
            if tick is None:
                continue

            currSL = self._initSLM * (1 + self._increment)**int((math.log(pos.high/pos.cost)/math.log(1 + self._step)))

            if tick.price < pos.cost*currSL:
                self._accountManager.closePos(tick.datetime, code, getattr(tick, DyStockTradeCommon.sellPrice), DyStockSellReason.stopLossStep)

    def onBars(self, bars):
        self.onTicks(bars)

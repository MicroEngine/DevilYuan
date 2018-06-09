import math
import numpy as np
import talib

from ..DyStockCtaTemplate import *
from ....Common.DyStockCommon import *
from ....Data.Utility.DyStockDataUtility import *


class DyST_IntraDayT(DyStockCtaTemplate):

    name = 'DyST_IntraDayT'
    chName = '日内T'

    barMode = 'bar1m'

    backTestingMode = barMode # 回测模式不能为日线回测，即bar1d
    liveMode = barMode

    broker = 'simu3'

    # 策略回测窗口参数格式: start:end;step
    param = OrderedDict\
                ([
                    ('ATR周期', '14'),
                    ('快速周期', '3'),
                    ('慢速周期', '20'),
                    ('标准差系数', '1')
                    #('标准差系数', '1:2;0.1')
                ])

    # UI
    signalDetailsHeader = ['时间', 'fast', 'slow']

    # 策略参数
    #targetCode = DyStockCommon.etf50 # 50ETF是2005.02上市的
    #targetCode = DyStockCommon.etf300 # 300ETF是2012.05上市的
    #targetCode = DyStockCommon.etf500 # 500ETF是2013.03上市的
    targetCode = '002722.SZ'

    bufSize = 100

    # 实盘参数
    atrPeriod = 14
    fastPeriod = 3
    slowPeriod = 20
    

    def __init__(self, ctaEngine, info, state, strategyParam=None):
        super().__init__(ctaEngine, info, state, strategyParam)

        if strategyParam is None: # 实盘参数
            pass

        else: # 回测参数
            self._atrPeriod = self._strategyParam['ATR周期']
            self._fastPeriod = self._strategyParam['快速周期']
            self._slowPeriod = self._strategyParam['慢速周期']
            self._stdCoef = self._strategyParam['标准差系数']

        self._curInit()

    def _onOpenConfig(self):
        """
            配置载入好的数据
        """
        code = self.targetCode

        self._highs = self._preparedData['highs'][code]
        self._lows = self._preparedData['lows'][code]
        self._closes = self._preparedData['closes'][code]

        self._preFast = self._preparedData['preFast'][code]
        self._preSlow = self._preparedData['preSlow'][code]

        self._preClose = self._preparedData['preClose'][code]

    def _curInit(self, date=None):
        self._highs = None
        self._lows = None
        self._closes = None

        self._preFast = None
        self._preSlow = None
        self._preClose = None

    @DyStockCtaTemplate.onOpenWrapper
    def onOpen(self, date, codes=None):
        # 当日初始化
        self._curInit(date)

        # 配置准备好的数据
        self._onOpenConfig()

        self._monitoredStocks.append(self.targetCode)

        return True

    @DyStockCtaTemplate.processPreparedDataAdjWrapper
    def _processPreparedDataAdj(self, tick, preClose=None):
        """
            处理准备数据除复权
            @preClose: 数据库里的前一日收盘价，由装饰器传入。具体策略无需关注。
        """
        adj = False
        if tick.preClose != preClose:
            adj = True

        self.processDataAdj(tick, preClose, self._preparedData, ['highs', 'lows', 'closes', 'preFast', 'preSlow'], isPrice=True, keyCodeFormat=True)

        if adj:
            self._onOpenConfig()

    @DyStockCtaTemplate.processPreparedPosDataAdjWrapper
    def _processPreparedPosDataAdj(self, tick, preClose=None):
        """
            处理准备数据除复权
            @preClose: 数据库里的前一日收盘价，由装饰器传入。具体策略无需关注。
        """
        pass

    def _processAdj(self, tick):
        """ 处理除复权 """
        return self._processPreparedDataAdj(tick) and self._processPreparedPosDataAdj(tick)

    def onBars(self, bars):
        bar = bars.get(self.targetCode)
        if bar is None:
            return

        # 停牌
        if bar.volume == 0:
            return

        # 处理除复权
        if not self._processAdj(bar):
            return

        # update buffer
        self._highs[:self.bufSize-1] = self._highs[1:]
        self._lows[:self.bufSize-1] = self._lows[1:]
        self._closes[:self.bufSize-1] = self._closes[1:]

        self._highs[-1] = bar.high
        self._lows[-1] = bar.low
        self._closes[-1] = bar.close

        fasts, slows, std = self._getAtrExtreme(self._highs, self._lows, self._closes,
                                                atrPeriod=self._atrPeriod, slowPeriod=self._slowPeriod, fastPeriod=self._fastPeriod)
        fast, slow = fasts[-1], slows[-1]

        if fast > slow + self._stdCoef*std: # buy
            self.buyByRatio(bar, 10, self.cAccountCapital, signalDetails=[bar.time, fast, slow])
        elif fast < slow - self._stdCoef*std: # sell
            self.sellByRatio(bar, 10, self.cAccountCapital, signalDetails=[bar.time, fast, slow])

        self._preFast = fast
        self._preSlow = slow


    #################### 开盘前的数据准备 ####################
    @classmethod
    def prepare(cls, date, dataEngine, info, codes=None, errorDataEngine=None, strategyParam=None, isBackTesting=False):
        code = DyST_IntraDayT.targetCode

        if isBackTesting:
            atrPeriod = strategyParam['ATR周期']
            fastPeriod = strategyParam['快速周期']
            slowPeriod = strategyParam['慢速周期']
        else:
            atrPeriod = cls.atrPeriod
            fastPeriod = cls.fastPeriod
            slowPeriod = cls.slowPeriod

        barSize = int(DyST_IntraDayT.barMode[3:-1])
        oneDayBarLen = math.ceil(4*60/barSize)
        dayNbr = math.ceil(DyST_IntraDayT.bufSize/oneDayBarLen)

        ticksEngine = dataEngine.ticksEngine

        if not ticksEngine.loadCodeN(code, [date, -dayNbr]):
            return None

        daysDf = ticksEngine.getDaysDataFrame(code)

        tickDf = ticksEngine.getDataFrame(code, adj=True, continuous=True)
        barDf = DyStockDataUtility.getIntraDayBars(tickDf, str(barSize) + 'min')

        highs = barDf['high'].values[-DyST_IntraDayT.bufSize:]
        lows = barDf['low'].values[-DyST_IntraDayT.bufSize:]
        closes = barDf['close'].values[-DyST_IntraDayT.bufSize:]

        fasts, slows, std = DyST_IntraDayT._getAtrExtreme(highs, lows, closes, atrPeriod=atrPeriod, slowPeriod=slowPeriod, fastPeriod=fastPeriod)

        return {'highs': {code: highs}, 'lows': {code: lows}, 'closes': {code: closes}, 'preFast': {code: fasts[-1]}, 'preSlow': {code: slows[-1]}, 'preClose': {code: daysDf.ix[-1, 'close']}}

    @classmethod
    def _getAtrExtreme(cls, highs, lows, closes, atrPeriod=14, slowPeriod=30, fastPeriod=3):
        """
            获取TTI ATR Exterme通道, which is based on 《Volatility-Based Technical Analysis》
            TTI is 'Trading The Invisible'

            @return: fasts, slows
        """
        # talib 的源码，它的 ATR 不是 N 日简单平均，而是类似 EMA 的方法计算的指数平均
        atr = talib.ATR(highs, lows, closes, timeperiod=atrPeriod)

        highsMean = talib.EMA(highs, 5)
        lowsMean = talib.EMA(lows, 5)
        closesMean = talib.EMA(closes, 5)

        atrExtremes = np.where(closes > closesMean,
                               ((highs - highsMean)/closes * 100) * (atr/closes * 100),
                               ((lows - lowsMean)/closes * 100) * (atr/closes * 100)
                               )

        fasts = talib.MA(atrExtremes, fastPeriod)
        slows = talib.EMA(atrExtremes, slowPeriod)

        return fasts, slows, np.std(atrExtremes[-slowPeriod:])
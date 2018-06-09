import operator

import DyCommon.DyTalib as DyTalib
from ..DyStockCtaTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DyST_MaWalk(DyStockCtaTemplate):

    name = 'DyST_MaWalk'
    chName = '均线游走'

    backTestingMode = 'bar1m'

    broker = 'simu2'

    curCodeBuyMaxNbr = 1

    # 策略实盘参数
    walkMa = 20 # 游走均线
    closeWalkMaPeriod = 30 # 前30日内，50%的收盘价在@walkMa之上
    closeUpWalkMaRatio = 50
    closeUpWalkMaNDays = 10 # 前10日，收盘价在@walkMa之上

    longMas = [20, 30, 60] # 均线多头排列
    prepareDaysSize = 10 # 需要准备的日线数据的天数

    volatilityNDays = 30 # 多少日的波动率
    volatilityThreshold = 6 # 波动率阈值

    swingNDays = 30 # swing的天数
    swingWindowSize = 3 # 计算swing用的滑动窗口大小

    erThreshold = 0.4 # @closeWalkMaPeriod日内的效率系数阈值

    #------------ 卖出信号相关参数 ------------
    sellSignalStopTimeThreshold = 4
    

    # UI
    dataHeader = [
                  '代码',
                  '名称',
                  '现价',
                  '涨幅(%)',
                  '最高涨幅(%)',

                  '现价{}均线差值比(%)'.format(walkMa),
                  '最低价{}均线差值比(%)'.format(walkMa),
                  '前{}日收盘在{}均线之上比(%)'.format(closeWalkMaPeriod, walkMa)
                  ]


    def __init__(self, ctaEngine, info, state, strategyParam=None):
        super().__init__(ctaEngine, info, state, strategyParam)

        self._curInit()

    def _onOpenConfig(self):
        self._monitoredStocks.extend(list(self._preparedData['preClose']))

    def _curInit(self, date=None):
        self._marketData = []

    @DyStockCtaTemplate.onOpenWrapper
    def onOpen(self, date, codes=None):
        # 当日初始化
        self._curInit(date)

        self._onOpenConfig()

        return True

    @DyStockCtaTemplate.onCloseWrapper
    def onClose(self):
        """
            策略每天收盘后的数据处理（由用户选择继承实现）
            持仓数据由策略模板类负责保存
            其他收盘后的数据，则必须由子类实现（即保存到@self._curSavedData）
        """
        #self._curSavedData['focus'] = self._focusInfoPool
        pass

    @DyStockCtaTemplate.processPreparedDataAdjWrapper
    def _processPreparedDataAdj(self, tick, preClose=None):
        """
            处理准备数据除复权
            @preClose: 数据库里的前一日收盘价，由装饰器传入。具体策略无需关注。
        """
        self.processDataAdj(tick, preClose, self._preparedData, ['walkMa'])
        self.processOhlcvDataAdj(tick, preClose, self._preparedData, 'days')

    @DyStockCtaTemplate.processPreparedPosDataAdjWrapper
    def _processPreparedPosDataAdj(self, tick, preClose=None):
        """
            处理准备数据除复权
            @preClose: 数据库里的前一日收盘价，由装饰器传入。具体策略无需关注。
        """
        self.processDataAdj(tick, preClose, self._preparedPosData, ['ma10', 'atr'], keyCodeFormat=False)

    def _processAdj(self, tick):
        """ 处理除复权 """
        return self._processPreparedDataAdj(tick) and self._processPreparedPosDataAdj(tick)

    def _addCodeMarketData(self, tick):
        ma = self._preparedData['walkMa'].get(tick.code)
        ratio = self._preparedData['closeUpWalkMaRatio'].get(tick.code)
        if ma is None or ratio is None:
            return

        data = [tick.code,
                tick.name,
                tick.price,
                (tick.price - tick.preClose)/tick.preClose*100,
                (tick.high - tick.preClose)/tick.preClose*100,
                (tick.price - ma)/ma*100,
                (tick.low - ma)/ma*100,
                ratio
                ]

        self._marketData.append(data)

    def _calcBuySignal(self, ticks):
        """
            计算买入信号
            @return: [buy code]
        """
        buyCodes = {}
        buyCodes1 = {}

        count = 0
        for code, tick in ticks.items():
            if tick.time < '14:55:00':
                continue

            walkMa = self._preparedData['walkMa'].get(code)
            if walkMa is None:
                continue

            if tick.volume > self._preparedData['days'][code][-1][-1]:
                continue

            """
            # 波动率
            swingBottomVolatilityMean = self._preparedData['swingBottomVolatilityMean'].get(code)
            if swingBottomVolatilityMean is None:
                continue

            # 当日波动率
            volatiliy = max(abs(tick.high - tick.low),
                            abs(tick.high - tick.preClose),
                            abs(tick.low - tick.preClose)
                            )
            volatiliy = volatiliy/tick.preClose*100

            if volatiliy > swingBottomVolatilityMean:
                continue
            """

            # 当日价格穿价游走均线
            if tick.low <= walkMa and tick.price > walkMa:
                buyCodes[code] = (tick.low - walkMa)/walkMa

            elif tick.high > tick.low:
                buyCodes1[code] = (min(tick.open, tick.price) - tick.low)/(tick.high - tick.low)

        buyCodes = sorted(buyCodes, key=lambda k: buyCodes[k], reverse=True)
        buyCodes1 = sorted(buyCodes1, key=lambda k: buyCodes1[k], reverse=True)

        buyCodes.extend(buyCodes1)

        return buyCodes

    def _calcSellSignal(self, ticks):
        """
            计算卖出信号
        """
        sellCodes = []
        for code, pos in self._curPos.items():
            if pos.availVolume == 0:
                continue

            tick = ticks.get(code)
            if tick is None:
                continue

            if tick.volume == 0:
                continue

            pnlRatio = (tick.price - pos.cost)/pos.cost*100

            if pnlRatio < -5 or pnlRatio > 10:
                sellCodes.append(code)
                continue

            if pos.holdingPeriod > 5 and pnlRatio > 5:
                sellCodes.append(code)
                continue

            """
            if pnlRatio < -5:
                sellCodes.append(code)
            elif pnlRatio > 10:
                pos.reserved = True

            if pos.reserved:
                if tick.price < self._preparedPosData[code]['ma10']:
                    sellCodes.append(code)
            """

        return sellCodes

    def _procSignal(self, ticks):
        """
            处理买入和卖出信号
        """
        buyCodes, sellCodes = self._calcSignal(ticks)

        self._execSignal(buyCodes, sellCodes, ticks)

    def _calcSignal(self, ticks):
        """
            计算信号
            @return: [buy code], [sell code]
        """
        return self._calcBuySignal(ticks), self._calcSellSignal(ticks)

    def _execBuySignal(self, buyCodes, ticks):
        """
            执行买入信号
        """
        for code in buyCodes:
            if code in self._curPos:
                continue

            tick = ticks.get(code)
            if tick is None:
                continue

            self.buyByRatio(tick, 20, self.cAccountCapital)

    def _execSellSignal(self, sellCodes, ticks):
        """
            执行卖出信号
        """
        for code in sellCodes:
            self.closePos(ticks.get(code))

    def _execSignal(self, buyCodes, sellCodes, ticks):
        """
            执行信号
            先卖后买，对于日线级别的回测，可以有效利用仓位。
        """
        self._execSellSignal(sellCodes, ticks)
        self._execBuySignal(buyCodes, ticks)

    def onTicks(self, ticks):
        """
            收到行情TICKs推送
            @ticks: {code: DyStockCtaTickData}
        """
        self._marketData = []
        for code, tick in ticks.items():
            # 停牌
            if tick.volume == 0:
                continue

            # 处理除复权
            if not self._processAdj(tick):
                continue

            self._addCodeMarketData(tick)

        # 处理信号
        self._procSignal(ticks)

        # put market data to UI
        self._marketData.sort(key=operator.itemgetter(3))
        self.putStockMarketMonitorUiEvent(data=self._marketData, newData=True, datetime_=self.marketDatetime)

    def onBars(self, bars):
        self.onTicks(bars)


    #################### 开盘前的数据准备 ####################
    @classmethod
    def _isMasLong(cls, maDf):
        """
            是不是均线多头排列
        """
        preMaDiff = None
        for i in range(len(DyST_MaWalk.longMas) - 1):
            ma = maDf.ix[-1, 'ma%s'%DyST_MaWalk.longMas[i]]
            nextMa = maDf.ix[-1, 'ma%s'%DyST_MaWalk.longMas[i+1]]

            if ma < nextMa:
                return False

            maDiff = ma - nextMa
            if preMaDiff is not None:
                if preMaDiff > maDiff:
                    return False

            preMaDiff = maDiff

        return True

    @classmethod
    def prepare(cls, date, dataEngine, info, codes=None, errorDataEngine=None, strategyParam=None, isBackTesting=False):
        """
            @date: 回测或者实盘时，此@date为前一交易日
            @return: {'preClose': {code: preClose},
                      'walkMa': {code: ma},
                      'closeUpWalkMaRatio': {code: ratio%},
                      'days': {code: [[OHLCV]]},
                      'er': {code: er},
                      'swingBottomVolatilityMean': {code: mean of swing bottom volatility}
                     }
        """
        daysEngine = dataEngine.daysEngine
        errorDaysEngine = errorDataEngine.daysEngine

        if not daysEngine.loadCodeTable(codes=codes):
            return None
        codes = daysEngine.stockCodes

        info.print('开始计算{0}只股票的指标...'.format(len(codes)), DyLogData.ind)
        progress = DyProgress(info)
        progress.init(len(codes), 100, 10)

        maxPeriod = max(DyST_MaWalk.longMas[-1], DyST_MaWalk.closeWalkMaPeriod + DyST_MaWalk.walkMa)

        preparedData = {}
        preCloseData = {}
        walkMaData = {}
        closeUpWalkMaRatioData = {}
        daysData = {}
        swingBottomVolatilityMeanData = {}
        erData = {}
        for code in codes:
            if not errorDaysEngine.loadCode(code, [date, -maxPeriod + 1], latestAdjFactorInDb=False):
                progress.update()
                continue

            # make sure enough periods
            df = errorDaysEngine.getDataFrame(code)
            if df.shape[0] < maxPeriod:
                progress.update()
                continue

            # MAs
            mas = set([DyST_MaWalk.walkMa] + DyST_MaWalk.longMas)
            maDf = DyStockDataUtility.getMas(df, mas, dropna=False)

            # 均线多头排列
            if not DyST_MaWalk._isMasLong(maDf):
                progress.update()
                continue

            # 收盘价游走均线占比
            walkMas = maDf['ma%s'%DyST_MaWalk.walkMa][-DyST_MaWalk.closeWalkMaPeriod:].values
            closes = df['close'][-DyST_MaWalk.closeWalkMaPeriod:].values

            ratio = (closes > walkMas).sum()/len(closes)*100
            if ratio < DyST_MaWalk.closeUpWalkMaRatio:
                progress.update()
                continue

            # 收盘价和游走均线价差
            close = df['close'][-1]
            walkMa = maDf['ma%s'%DyST_MaWalk.walkMa][-1]

            if not (0 < (close - walkMa)/close < 0.1):
                progress.update()
                continue

            # 收盘价游走均线之上日数
            walkMas = maDf['ma%s'%DyST_MaWalk.walkMa][-DyST_MaWalk.closeUpWalkMaNDays:].values
            closes = df['close'][-DyST_MaWalk.closeUpWalkMaNDays:].values

            if (closes < walkMas).sum() > 0:
                progress.update()
                continue

            # 无跌停
            if (df['close'][-DyST_MaWalk.closeUpWalkMaNDays-1:].pct_change().dropna() <= DyStockCommon.limitDownPct/100).sum() > 0:
                progress.update()
                continue

            # 无涨停
            if (df['close'][-DyST_MaWalk.closeUpWalkMaNDays-1:].pct_change().dropna() >= DyStockCommon.limitUpPct/100).sum() > 0:
                progress.update()
                continue

            # Efficiency ratio
            closes = df['close'][-DyST_MaWalk.closeWalkMaPeriod:]
            direction = closes[-1] - closes[0]
            volatility = (closes - closes.shift(1)).abs().sum()
            er = direction/volatility
            if er < DyST_MaWalk.erThreshold:
                progress.update()
                continue

            # 波动率
            volatilityMean = DyStockDataUtility.getVolatility(df[-DyST_MaWalk.volatilityNDays-1:]).mean()
            if volatilityMean > DyST_MaWalk.volatilityThreshold:
                progress.update()
                continue

            # 最近3天波动率
            volatility = DyStockDataUtility.getVolatility(df[-4:])
            if not 10 > volatility.mean() > 2:
                progress.update()
                continue

            if volatility.max() > 10:
                progress.update()
                continue

            # Swing波动率
            if 0:
                volatility = DyStockDataUtility.getVolatility(df[-DyST_MaWalk.swingNDays-1:])
                extremas, peaks, bottoms = DyStockDataUtility.swings(df[-DyST_MaWalk.swingNDays-1:], w=DyST_MaWalk.swingWindowSize)
                bottoms = bottoms[bottoms <= DyST_MaWalk.volatilityThreshold] # 剔除底部大波动的点
                if bottoms.empty:
                    continue

                swingBottomVolatilityMean = volatility[bottoms.index].mean()
                print(code, swingBottomVolatilityMean)

            #-------------------- set prepared data for each code --------------------
            preCloseData[code] = close # preClose
            walkMaData[code] = walkMa # walk ma
            closeUpWalkMaRatioData[code] = ratio # 收盘价游走均线占比
            daysData[code] = df.ix[-DyST_MaWalk.prepareDaysSize:, ['open', 'high', 'low', 'close', 'volume']].values.tolist() # 日线OHLCV
            #swingBottomVolatilityMeanData[code] = swingBottomVolatilityMean
            erData[code] = er

            progress.update()

        preparedData['preClose'] = preCloseData
        preparedData['walkMa'] = walkMaData
        preparedData['closeUpWalkMaRatio'] = closeUpWalkMaRatioData
        preparedData['days'] = daysData
        preparedData['er'] = erData
        preparedData['swingBottomVolatilityMean'] = swingBottomVolatilityMeanData

        info.print('计算{}只股票的指标完成, 共选出{}只股票'.format(len(codes), len(preCloseData)), DyLogData.ind)

        return preparedData

    @classmethod
    def preparePos(cls, date, dataEngine, info, posCodes=None, errorDataEngine=None, strategyParam=None, isBackTesting=False):
        """
            策略开盘前持仓准备数据
            @date: 前一交易日
            @return:
        """
        if not posCodes: # not positions
            return {}

        errorDaysEngine = errorDataEngine.daysEngine

        data = {}
        for code in posCodes:
            if not errorDaysEngine.loadCode(code, [date, -200], latestAdjFactorInDb=False):
                return None

            df = errorDaysEngine.getDataFrame(code)

            highs, lows, closes = df['high'].values, df['low'].values, df['close'].values

            # channel upper and lower
            atr = DyTalib.ATR(highs, lows, closes, timeperiod=DyST_MaWalk.walkMa)

            data[code] = {'preClose': closes[-1], # 为了除复权
                          'ma10': df['close'][-10:].mean(),
                          'atr': atr
                          }

        return data

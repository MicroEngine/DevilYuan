from ..DyStockCtaTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DyST_AbnormalVolatility(DyStockCtaTemplate):
    name = 'DyST_AbnormalVolatility'
    chName = '异常波动'
    backTestingMode = 'bar1d'

    broker = 'simu1'

    #------------ 策略prepare参数 ------------
    feedNDays = 80 # 需要向前准备的天数

    thresholdNDays = 20
    volatilityMeanThreshold = 4 # 波动率阈值
    volatilityMaxThreshold = 10 # 波动率阈值

    longMas = [10, 20, 30]
    centralMa = 10
    longMaDays = [3, 4]

    #--------------- 策略参数 ---------------
    upZscore = 2
    sellSignalTime = '09:35:00'
    maxBuyNbr = 5


    def __init__(self, ctaEngine, info, state, strategyParam=None):
        super().__init__(ctaEngine, info, state, strategyParam)

        self._curInit()

    def _onOpenConfig(self):
        self._monitoredStocks.extend(list(self._preparedData['preClose']))

    def _curInit(self, date=None):
        pass

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
        pass

    @DyStockCtaTemplate.processPreparedDataAdjWrapper
    def _processPreparedDataAdj(self, tick, preClose=None):
        """
            处理准备数据除复权
            @preClose: 数据库里的前一日收盘价，由装饰器传入。具体策略无需关注。
        """
        pass

    @DyStockCtaTemplate.processPreparedPosDataAdjWrapper
    def _processPreparedPosDataAdj(self, tick, preClose=None):
        """
            处理准备数据除复权
            @preClose: 数据库里的前一日收盘价，由装饰器传入。具体策略无需关注。
        """
        self.processDataAdj(tick, preClose, self._preparedPosData, ['ma10', 'm20'], keyCodeFormat=False)

    def _processAdj(self, tick):
        """ 处理除复权 """
        return self._processPreparedDataAdj(tick) and self._processPreparedPosDataAdj(tick)

    def _calcBuySignal(self, ticks):
        """
            计算买入信号
            @return: [buy code]
        """
        buyCodes = {}

        for code, tick in ticks.items():
            if tick.open < tick.preClose:
                continue

            ratio = (tick.price - tick.preClose)/tick.preClose*100
            if ratio < 0 or tick.high == tick.price:
                continue

            if (tick.high - tick.price)/tick.preClose*100 > 2:
                continue

            up = self._preparedData['up'].get(code)
            if up is None:
                continue

            upMean, upStd = up
            zscore = (ratio - upMean)/upStd
            if zscore < self.upZscore:
                continue

            #buyCodes[code] = zscore
            buyCodes[code] = (tick.high - tick.price)/tick.preClose*100

        buyCodes = sorted(buyCodes, key=lambda k: buyCodes[k], reverse=False)

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

            maxVolatility = self._preparedPosData[code]['maxVolatility']
            dropDownRatio = (pos.closeHigh - tick.price)/pos.closeHigh*100
            #assert dropDownRatio >= 0, print(self._curTDay, code)
            if dropDownRatio > maxVolatility:
                sellCodes.append(code)

            """
            pnlRatio = (tick.price - pos.cost)/pos.cost*100

            if pnlRatio < 0:
                if pnlRatio < -5:
                    sellCodes.append(code)
            
            elif pnlRatio > 0: # 止盈
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
        trueBuyCodes = []
        for code in buyCodes:
            if code in self._curPos:
                continue

            tick = ticks.get(code)
            if tick is None:
                continue

            trueBuyCodes.append(code)

        trueBuyCodes = trueBuyCodes[:self.maxBuyNbr]
        cashRatio = self.getCashOverCapital()
        for code in trueBuyCodes:
            self.buyByRatio(ticks.get(code), min(30, 1/len(trueBuyCodes)*cashRatio), self.cAccountCapital)

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

    @DyStockCtaTemplate.onTicksWrapper
    def onTicks(self, ticks):
        """
            收到行情TICKs推送
            @ticks: {code: DyStockCtaTickData}
        """
        for code, tick in ticks.items():
            # 停牌
            if tick.volume == 0:
                continue

            # 处理除复权
            if not self._processAdj(tick):
                continue

        # 处理信号
        self._procSignal(ticks)

    @DyStockCtaTemplate.onBarsWrapper
    def onBars(self, bars):
        self.onTicks(bars)

    #################### 开盘前的数据准备 ####################
    @classmethod
    def prepare(cls, date, dataEngine, info, codes=None, errorDataEngine=None, strategyParam=None, isBackTesting=False):
        """
            @date: 前一交易日
            @return: {'preClose': {code: preClose},
                      'up': {code: [mean, std]}
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

        maxPeriod = DyST_AbnormalVolatility.feedNDays

        # 均线相关的固定数据
        mas = set(DyST_AbnormalVolatility.longMas + [DyST_AbnormalVolatility.centralMa])
        mas = list(mas)
        mas.sort()

        longMaNames = ['ma%s'%x for x in DyST_AbnormalVolatility.longMas]
        centralMaName = 'ma%s'%DyST_AbnormalVolatility.centralMa

        preparedData = {}
        preCloseData = {}
        upData = {}
        for code in codes:
            if not errorDaysEngine.loadCode(code, [date, -maxPeriod + 1], latestAdjFactorInDb=False):
                progress.update()
                continue

            # make sure enough periods
            df = errorDaysEngine.getDataFrame(code)
            if df.shape[0] < maxPeriod:
                progress.update()
                continue

            opens, highs, lows, closes = df['open'], df['high'], df['low'], df['close']
            
            # 波动率
            volatility = DyStockDataUtility.getVolatility(df)
            volatility = volatility[-DyST_AbnormalVolatility.thresholdNDays:]

            if volatility.mean() > DyST_AbnormalVolatility.volatilityMeanThreshold:
                progress.update()
                continue

            if volatility.max() > DyST_AbnormalVolatility.volatilityMaxThreshold:
                progress.update()
                continue

            # 上涨时的波动率
            preCloses = closes.shift(1)
            highVolatility = (df['high'] - preCloses)/preCloses * 100
            upVolatility = highVolatility[highVolatility > 0]
            if len(upVolatility) < DyST_AbnormalVolatility.thresholdNDays:
                progress.update()
                continue

            upVolatility = upVolatility[-DyST_AbnormalVolatility.thresholdNDays:]

            # mean and std
            upMean = upVolatility.mean()
            upStd = upVolatility.std()

            maDf = DyStockDataUtility.getMas(df, [5, 60], dropna=True)

            if (df['close'][-DyST_AbnormalVolatility.thresholdNDays:] < maDf['ma60'][-DyST_AbnormalVolatility.thresholdNDays:]).sum() > 0:
                progress.update()
                continue

            if closes[-1] < maDf['ma5'][-1]:
                progress.update()
                continue

            # 均线多头
            """
            maDf = DyStockDataUtility.getMas(df, mas, dropna=True)

            longDayNbr = DyStockDataUtility.getMasLong(maDf[longMaNames], diffLong=True)
            if not DyST_AbnormalVolatility.longMaDays[0] <= longDayNbr <= DyST_AbnormalVolatility.longMaDays[1]:
                progress.update()
                continue

            if (df['close'][-longDayNbr:] < maDf[centralMaName][-longDayNbr:]).sum() > 0:
                progress.update()
                continue
            """

            #-------------------- set prepared data for each code --------------------
            preCloseData[code] = closes[-1] # preClose
            upData[code] = [upMean, upStd]

            progress.update()

        preparedData['preClose'] = preCloseData
        preparedData['up'] = upData

        info.print('计算{}只股票的指标完成, 共选出{}只股票'.format(len(codes), len(preCloseData)), DyLogData.ind)

        return preparedData

    @classmethod
    def preparePos(cls, date, dataEngine, info, posCodes=None, errorDataEngine=None, strategyParam=None, isBackTesting=False):
        """
            策略开盘前持仓准备数据
            @date: 前一交易日
            @return: None - error
        """
        if not posCodes: # not positions
            return {}

        errorDaysEngine = errorDataEngine.daysEngine

        data = {}
        for code in posCodes:
            if not errorDaysEngine.loadCode(code, [date, -20], latestAdjFactorInDb=False):
                return None

            df = errorDaysEngine.getDataFrame(code)

            highs, lows, closes = df['high'].values, df['low'].values, df['close'].values

            volatility = DyStockDataUtility.getVolatility(df)
            volatility = volatility[-DyST_AbnormalVolatility.thresholdNDays:]


            data[code] = {'preClose': closes[-1], # 为了除复权
                          'ma10': df['close'][-10:].mean(),
                          'ma20': df['close'][-20:].mean(),
                          'maxVolatility': volatility.max()
                          }

        return data

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_LimitUpPredict(DyStockSelectStrategyTemplate):
    """
        当日涨停股票预测
    """
    name = 'DySS_LimitUpPredict'
    chName = '涨停预测'

    autoFillDays = True
    optimizeAutoFillDays = True
    continuousTicks = False

    colNames = ['代码', '名称',
                '最高涨幅(%)',
                'preClose/MA20',
                '前日RSI',
                '前涨停数', # 前20日
                '换手率(%)', # 当日换手率
                '前60日涨幅(%)', # 前60日最低价到前一交易日的涨幅
                '前60日最大涨幅衰减(%)', # 前60日的最大涨幅衰减到当日的值
                ####################
                '首次high时间',
                '当日聪明钱指标', # 当日聪明钱指标，越大越好
                '前5日聪明钱指标',
                ]

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('当日最高涨幅不低于(%)', 5),
                    ('前20日涨停数不高于', 2),
                    ('前60日涨幅不高于(%)', 30),
                    ('前5日聪明钱指标', '-20,20'), # 非闭合方式
                ])


    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._highRatio             = param['当日最高涨幅不低于(%)']
        self._preLimitUpNbr         = param['前20日涨停数不高于']
        self._pre60Increase         = param['前60日涨幅不高于(%)']
        self._pre5SmartMoney        = [int(v) for v in param['前5日聪明钱指标'].split(',')]

    def onDaysLoad(self):
        return self._baseDate, -60

    def onTicksLoad(self):
        return self._baseDate, -5

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine
        self._ticksEngine = errorDataEngine.ticksEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes

        self._preCloseDict = {} # {code: preClose}
        self._highDict = {} # {code: high}

    def _checkHighRatio(self, code, df):
        if df.shape[0] < 2:
            return None

        close = df.ix[-1, 'close']
        preClose = df.ix[-2, 'close']
        high = df.ix[-1, 'high']
        open = df.ix[-1, 'open']

        highRatio = (high - preClose)/preClose*100
        if highRatio < self._highRatio:
            return None

        # 剔除一字板涨停
        if df.ix[-1, 'high'] == df.ix[-1, 'low']:
            return None

        # 剔除涨停开盘
        if (open - preClose)/preClose*100 >= DyStockCommon.limitUpPct:
            return None

        # save
        self._preCloseDict[code] = preClose
        self._highDict[code] = high

        return highRatio

    def _checkPreCloseOverMa20(self, df):
        maDf = DyStockDataUtility.getMas(df, [20])

        try:
            preMa = maDf.ix[-2, 'ma20']
            preClose = df.ix[-2, 'close']
            preClosePos = preClose/preMa
        except Exception as ex:
            return None

        if not 0.8 <= preClosePos <= 1.3:
            return None

        return preClosePos

    def _checkPreRsi(self, df):
        """
            涨停前日的RSI
        """
        rsi = talib.RSI(df['close'].values, timeperiod=14)
        if len(rsi) < 2:
            return None

        preRsi = rsi[-2]

        if not 20 <= preRsi <= 80:
            return None

        return preRsi
        
    def _checkPreLimitUpNbr(self, df):
        """
            前20日的涨停数（不含当日涨停）
        """
        df = df[-22:-1]
        closePctChange = df['close'].pct_change()

        limitUpBool = closePctChange >= DyStockCommon.limitUpPct/100
        limitUpNbr = limitUpBool.sum()

        if limitUpNbr > self._preLimitUpNbr:
            return None

        # !!!very ticky, that @limitUpNbr is numpy.int64, which cannot be showed in QTableWidget
        return int(limitUpNbr)

    def _checkPre60Increase(self, df):
        low = df.ix[:-1, 'low'].min()
        preClose = df.ix[-2, 'close']

        pre60Increase = (preClose - low)/low*100
        if pre60Increase > self._pre60Increase:
            return None

        return pre60Increase

    def _checkPre60MaxIncreaseDecay(self, df):
        """
            前60日最大涨幅衰减
            越靠当日的最大涨幅，对当日的影响就越大。越小的影响，更有意义。
            @return: -1代表不考虑衰减
        """
        lows = df.ix[:-1, 'low']
        minPos = df.index.get_loc(lows.argmin())

        highs = df.ix[minPos:-1, 'high']
        maxPos = df.index.get_loc(highs.argmax()) # !!!argmax和idxmax返回一样的值

        # 若是跌幅则忽略
        if maxPos < minPos:
            return -1
        
        increaseDays = maxPos - minPos

        low = df.ix[minPos, 'low']
        high = df.ix[maxPos, 'high']

        increase = (high - low)/low*100

        # 最高价到当日的天数
        intervalDays = df.shape[0] - 1 - maxPos

        decayIncrease = increase * (1 - math.sqrt(increaseDays)/100)**intervalDays

        if decayIncrease > 20:
            return None

        return decayIncrease


    ##################################################################################################################
    ##################################################################################################################
    def _checkFirstHighTime(self, code, df):
        highPoint = self._preCloseDict[code] * (1 + self._highRatio/100)
        highPointBool = df['price'] >= highPoint

        if highPointBool.sum() == 0:
            high = df['price'].max()
            if self._highDict[code] != high:
                self._info.print('[{0}:{1}]万得的{2}日线high={3}跟新浪Tick数据high={4}不一致'.format(code,
                                                                                        self._stockAllCodes[code],
                                                                                        df.index[0].strftime("%Y-%m-%d"),
                                                                                        self._highDict[code],
                                                                                        high), DyLogData.warning)

            self._info.print('忽略[{0}:{1}]'.format(code, self._stockAllCodes[code]), DyLogData.warning)
            return None

        firstHighTime = highPointBool.idxmax()
        firstHighTime = firstHighTime.strftime('%H:%M:%S')

        if firstHighTime > '11:30:00':
            return None

        return firstHighTime

    def _checkCurSmartMoney(self, df, firstHighTime):
        barDf = DyStockDataUtility.getIntraDayBars(df, '1min')

        # smart money
        diffBarDf = np.log(barDf).diff().dropna()

        diffBarDf = diffBarDf[:diffBarDf.index[0].strftime('%Y-%m-%d') + ' ' + firstHighTime]

        smartMoney = self._calcSmartMoney(diffBarDf, isBothLowVolume=True)

        if smartMoney < 0:
            return None

        return smartMoney*100

    def _calcSmartMoney(self, diffBarDf, isBothLowVolume=False):
        if isBothLowVolume:
            # 上涨缩量好
            increaseBool = diffBarDf['close'] > 0
            increaseDiffBarDf = diffBarDf[increaseBool]
            increaseSmartMoney = (increaseDiffBarDf['close']*-increaseDiffBarDf['volume']).sum()

            # 下跌缩量好
            decreaseBool = diffBarDf['close'] < 0
            decreaseDiffBarDf = diffBarDf[decreaseBool]
            decreaseSmartMoney = (decreaseDiffBarDf['close']*decreaseDiffBarDf['volume']).sum()

            smartMoney = increaseSmartMoney + decreaseSmartMoney
        else:
            smartMoney = (diffBarDf['close']*diffBarDf['volume']).sum()

        return smartMoney

    def _checkPre5SmartMoney(self, dfs):
        totalSmartMoney = 0
        for df in dfs.values():
            barDf = DyStockDataUtility.getIntraDayBars(df, '1min')

            # smart money
            diffBarDf = np.log(barDf).diff().dropna()

            smartMoney = self._calcSmartMoney(diffBarDf, isBothLowVolume=True)

            totalSmartMoney += smartMoney*100

        if self._pre5SmartMoney[0] < totalSmartMoney < self._pre5SmartMoney[1]:
            return totalSmartMoney

        return None


    ###################################################################################################################
    ###################################################################################################################
    def onStockDays(self, code, df):
        highRatio = self._checkHighRatio(code, df)
        if highRatio is None:
            return

        preCloseMaPos = self._checkPreCloseOverMa20(df)
        if preCloseMaPos is None:
            return

        preRsi = self._checkPreRsi(df)
        if preRsi is None:
            return

        limitUpNbr = self._checkPreLimitUpNbr(df)
        if limitUpNbr is None:
            return

        pre60Increase = self._checkPre60Increase(df)
        #if pre60Increase is None:
        #    return

        pre60MaxIncreaseDecay = self._checkPre60MaxIncreaseDecay(df)
        if pre60MaxIncreaseDecay is None:
            return

        # 设置结果
        row = [code, self._stockAllCodes[code],
               highRatio,
               preCloseMaPos,
               preRsi,
               limitUpNbr,
               df.ix[-1, 'turn'],
               pre60Increase,
               pre60MaxIncreaseDecay
               ]
        self._result.append(row)

    def onStockTicks(self, code, dfs):
        days = sorted(dfs)
        df = dfs[days[-1]] # 当日tick DF

        firstHighTime = self._checkFirstHighTime(code, df)
        if firstHighTime is None:
            self.removeFromResult(code)
            return

        curSmartMoney = self._checkCurSmartMoney(df, firstHighTime)
        if curSmartMoney is None:
            self.removeFromResult(code)
            return

        pre5SmartMoney = self._checkPre5SmartMoney({day: dfs[day] for day in days[:-1]})
        if pre5SmartMoney is None:
            self.removeFromResult(code)
            return

        # 设置结果
        partRow = [firstHighTime,
                   curSmartMoney,
                   pre5SmartMoney
                   ]

        row = self.getFromResult(code)
        row.extend(partRow)

    ###################################################################################################################
    ###################################################################################################################

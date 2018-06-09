from statsmodels.tsa import stattools
from sklearn.decomposition import PCA

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_LimitUpAnalysis(DyStockSelectStrategyTemplate):
    """
        当日涨停股票分析
    """
    name = 'DySS_LimitUpAnalysis'
    chName = '涨停分析'

    autoFillDays = True
    optimizeAutoFillDays = True
    continuousTicks = False

    colNames = ['代码', '名称',
                '开盘比(%)', # open/preClose*100
                'close/MA20', 'preClose/MA20',
                '指数close/MA20',
                '均线多头', # 前一交易日，1： 5, 10, 20, 30均线多头排列，0：非均线多头排列
                '前10日波动(%)均值', '前10日波动(%)std',
                '前日RSI',
                '前涨停数', '涨停间隔均值(日)',
                'peak突破数/∑',
                '前10日量/20日量的均值',
                '当日量/前5日量均值',
                '换手率(%)',
                #'ADF检验p值',
                ####################
                '开盘30分量/日量(%)',
                '收盘30分量/日量(%)',

                '首次涨停时间',
                '最后涨停时间',
                '首次涨停前量/日量(%)',
                '首次涨停前量/前5日均量',

                '开板数',
                '开板量/日量(%)',

                '1日开盘30分涨幅(%)',

                '聪明钱指标', # 当日聪明钱指标，越大越好
                ]

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 60),
                    ('当日涨停', 1),
                    ('当日仅触及涨停', 1)
                ])

    # 策略私有参数
    ma = 20

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._forwardNTDays         = param['向前N日周期']
        self._oklimitUp             = True if param['当日涨停'] else False
        self._noklimitUp            = True if param['当日仅触及涨停'] else False

    def onDaysLoad(self):
        return self._baseDate, -(self._forwardNTDays + self.ma)

    def onTicksLoad(self):
        return self._baseDate, -5

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine
        self._ticksEngine = errorDataEngine.ticksEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes

        self._indexDataDict = {}

    def onIndexDays(self, code, df):
        """ 指数日线数据 """
        
        closeMaPos, preCloseMaPos = self._closeMaPos(df)

        self._indexDataDict[code] = closeMaPos

    def _isValidLimitUp(self, df):
        """
            是否是当日涨停
        """
        if df.shape[0] < 2:
            return False

        close = df.ix[-1, 'close']
        preClose = df.ix[-2, 'close']
        high = df.ix[-1, 'high']

        if self._oklimitUp and self._noklimitUp:
            if not (high - preClose)/preClose*100 >= DyStockCommon.limitUpPct:
                return False

        elif self._oklimitUp:
            if not ((high - preClose)/preClose*100 >= DyStockCommon.limitUpPct and close == high):
                return False

        elif self._noklimitUp:
            if not ((high - preClose)/preClose*100 >= DyStockCommon.limitUpPct and close != high):
                return False
        else:
            return False

        # 剔除一字板涨停
        if df.ix[-1, 'high'] == df.ix[-1, 'low']:
            return False

        return True

    def _closeMaPos(self, df):
        """
            涨停日的均线位置，涨停前日的均线位置（20日均线）
        """
        maDf = DyStockDataUtility.getMas(df, [self.ma])
        maName = 'ma%s'%self.ma

        try:
            ma = maDf.ix[-1, maName]
            close = df.ix[-1, 'close']
            closePos = close/ma
        except Exception as ex:
            closePos = None

        try:
            preMa = maDf.ix[-2, maName]
            preClose = df.ix[-2, 'close']
            preClosePos = preClose/preMa
        except Exception as ex:
            preClosePos = None

        return closePos, preClosePos

    def _volatility(self, df):
        """
            涨停前10日的每日波动率的均值和标准差
        """
        df = df[-11:]

        highVolatility = (df['high'] - df['close'].shift(1))/df['close'].shift(1)
        lowVolatility = (df['low'] - df['close'].shift(1))/df['close'].shift(1)
        highLowVolatility = highVolatility - lowVolatility

        df = pd.concat([highVolatility, lowVolatility, highLowVolatility], axis=1)
        df = abs(df)
        maxValitality = df.max(axis=1)
        maxValitality *= 100

        return maxValitality.mean(), maxValitality.std()

    def _preRsi(self, df):
        """
            涨停前日的RSI
        """
        rsi = talib.RSI(df['close'].values, timeperiod=14)

        return rsi[-2]

    def _countPreLimitUp(self, df):
        """
            N周期日的涨停数（不含当日涨停），涨停间隔周期的均值
        """
        closePctChange = df['close'].pct_change()

        limitUpBool = closePctChange >= DyStockCommon.limitUpPct/100
        limitUpNbr = limitUpBool.sum()
        if limitUpBool[-1]: # 剔除当日涨停
            limitUpNbr -= 1
        
        s = pd.Series(list(range(df.shape[0])), index=df.index)
        limitUpS = s[limitUpBool]

        limitUpIntervalMean = (limitUpS - limitUpS.shift(1)).mean()

        return int(limitUpNbr), None if np.isnan(limitUpIntervalMean) else int(limitUpIntervalMean)

    def _countBreakoutPeaks(self, df):
        """
            涨停日收盘价突破N周期内的极大值个数, 极大值总数
        """
        close = df.ix[-1, 'close']

        # peaks
        extremas, peaks, bottoms = DyStockDataUtility.rwExtremas(df)

        breakoutCount = 0
        for peak in peaks:
            if close > peak:
                breakoutCount += 1

        return breakoutCount, peaks.size

    def _countVolume(self, df):
        """
            涨停前10日的每日量能跟20日量能之比的均值,
            涨停日量能/涨停前5日量能均值
        """
        volume = df.ix[-1, 'volume']

        df = df[-30:-1]

        volumeMaDf = DyStockDataUtility.getMas(df, [5, 20], dropna=False, indicator='volume')

        ratioSeries = df['volume']/volumeMaDf['ma20']

        return ratioSeries.mean(), volume/volumeMaDf.ix[-1, 'ma5']

    def _adfTest(self, df):
        """
            ADF Test
            p值越大：随机漫步，可能是趋势
            p值越小：均值回归
        """
        df = df[-21:-1]

        result = stattools.adfuller(df['close'], 1)

        return result[1]

    def _masAttack(self, df):
        maDf = DyStockDataUtility.getMas(df, [5, 10, 20, 30])

        try:
            if maDf.ix[-2, 'ma5'] >= maDf.ix[-2, 'ma10'] >= maDf.ix[-2, 'ma20'] >= maDf.ix[-2, 'ma30']:
                return 1
            else:
                return 0
        except Exception:
            return None
                

    ##################################################################################################################
    ##################################################################################################################
    def _curTickLimitUpAnalysis(self, df):
        """
            当日Tick涨停分析
        """
        def _count(df):
            nonlocal high
            nonlocal firstLimitUpTime
            nonlocal lastLimitUpTime
            nonlocal limitUpBreakdownCount
            nonlocal limitUpBreakdownVolume

            # 判断是涨停DF还是非涨停DF
            if df.ix[0, 'price'] < high: # 非涨停
                if firstLimitUpTime is not None:
                    limitUpBreakdownCount += 1

                    limitUpBreakdownVolume += df['volume'].sum()

            else: # 涨停
                if firstLimitUpTime is None:
                    firstLimitUpTime = df.index[0]

                lastLimitUpTime = df.index[0]

        high = df['price'].max()
        volume = df['volume'].sum()

        firstLimitUpTime = None
        lastLimitUpTime = None
        limitUpBreakdownCount = 0
        limitUpBreakdownVolume = 0 # 开板总量

        boolSeries = df['price'] == high
        df.groupby((boolSeries != boolSeries.shift(1)).cumsum()).apply(_count)
        
        limitUpBreakdownVolumeRatio = limitUpBreakdownVolume/volume * 100

        return firstLimitUpTime, lastLimitUpTime, limitUpBreakdownCount, limitUpBreakdownVolumeRatio

    def _curTickVolumeAnalysis(self, df, firstLimitUpTime, dfs):
        volume = df['volume'].sum()
        day = df.index[0].strftime('%Y-%m-%d')

        # open30min and close30min volume
        open30Volume = df[:day + ' 10:00:00']['volume'].sum()
        close30Volume = df[day + ' 14:30:00':]['volume'].sum()

        open30VolumeRatio = open30Volume/volume*100
        close30VolumeRatio = close30Volume/volume*100

        # volume of before limitup time over current day volume
        beforeFirstLimitUpVolume = df[:firstLimitUpTime]['volume'].sum()
        beforeFirstLimitUpVolumeRatio = beforeFirstLimitUpVolume/volume*100

        # volume of before limitup time over average previous 5 days volume of before limitup time
        days = sorted(dfs)
        firstLimitUpTime_ = firstLimitUpTime.strftime('%H:%M:%S')
        days5Volume = 0
        for dayNbr, day_ in enumerate(days[:-1], 1):
            days5Volume += dfs[day_][:day_ + ' ' + firstLimitUpTime_]['volume'].sum()

        beforeFirstLimitUpVolume5DaysRatio = (beforeFirstLimitUpVolume/(days5Volume/dayNbr)) if days5Volume > 0 else None

        return open30VolumeRatio, close30VolumeRatio, beforeFirstLimitUpVolumeRatio, beforeFirstLimitUpVolume5DaysRatio

    def _increase1Day30Min(self, code, df):
        close = df.ix[-1, 'price']
        day = df.index[0].strftime('%Y-%m-%d')

        if not self._ticksEngine.loadCodeN(code, [day, 1]):
            return None

        dfs = self._ticksEngine.getDataFrame(code, adj=True, continuous=False)
        if len(dfs) < 2:
            return None

        days = sorted(dfs)
        nextDay = days[-1]
        df = dfs[nextDay][:nextDay + ' 10:00:00']
        close30Min = df.ix[-1, 'price']

        return (close30Min - close)/close * 100

    def _smartMoney(self, df):
        # 合成Bar, 右闭合
        # 缺失的Bar设为NaN
        barDf = df.resample('1min', closed='right', label='right')[['price', 'volume']].agg(OrderedDict([('price', 'ohlc'), ('volume', 'sum')]))
        barDf.dropna(inplace=True) # drop缺失的Bars

        # remove multi-index of columns
        barDf = pd.concat([barDf['price'], barDf['volume']], axis=1)
        barDf = barDf[barDf['volume'] > 0]

        # smart money
        diffBarDf = np.log(barDf).diff().dropna()

        smartMoney = (diffBarDf['close']*diffBarDf['volume']).sum()

        return smartMoney*100


    ###################################################################################################################
    ###################################################################################################################
    def onStockDays(self, code, df):
        if not self._isValidLimitUp(df):
            return

        openRatio = (df.ix[-1, 'open'] - df.ix[-2, 'close'])/df.ix[-2, 'close']*100

        closeMaPos, preCloseMaPos = self._closeMaPos(df)

        masAttack = self._masAttack(df)

        volatilityMean, volatilityStd = self._volatility(df)

        preRsi = self._preRsi(df)

        limitUpNbr, limitUpIntervalMean = self._countPreLimitUp(df)

        breakoutCount, peaksNbr = self._countBreakoutPeaks(df)

        volume10RatioMean, volume5MeanRatio = self._countVolume(df)

        #adfTestPvalue = self._adfTest(df)

        # 设置结果
        row = [code, self._stockAllCodes[code],
               openRatio,
               closeMaPos, preCloseMaPos,
               self._indexDataDict[self._daysEngine.getIndex(code)], # 指数close/MA20
               masAttack,
               volatilityMean, volatilityStd,
               preRsi,
               limitUpNbr, limitUpIntervalMean,
               '%d/%d'%(breakoutCount, peaksNbr),
               volume10RatioMean, volume5MeanRatio,
               df.ix[-1, 'turn']
               #adfTestPvalue
               ]
        self._result.append(row)

    def onStockTicks(self, code, dfs):
        days = sorted(dfs)
        df = dfs[days[-1]]

        #barDf = DyStockDataUtility.getMinBars(dfs, 1)

        firstLimitUpTime, \
        lastLimitUpTime, \
        limitUpBreakdownCount, \
        limitUpBreakdownVolumeRatio = self._curTickLimitUpAnalysis(df)

        open30VolumeRatio, \
        close30VolumeRatio, \
        beforeFirstLimitUpVolumeRatio, \
        beforeFirstLimitUpVolume5DaysRatio = self._curTickVolumeAnalysis(df, firstLimitUpTime, dfs)

        # 后1日开盘30分的涨幅
        Increase1Day30Min = self._increase1Day30Min(code, df)

        smartMoney = self._smartMoney(df)

        # 设置结果
        partRow = [open30VolumeRatio,
                   close30VolumeRatio,

                   firstLimitUpTime.strftime('%H:%M:%S'),
                   lastLimitUpTime.strftime('%H:%M:%S'),
                   beforeFirstLimitUpVolumeRatio,
                   beforeFirstLimitUpVolume5DaysRatio,

                   limitUpBreakdownCount,
                   limitUpBreakdownVolumeRatio,

                   Increase1Day30Min,
                   smartMoney,
                   ]

        row = self.getFromResult(code)
        row.extend(partRow)

    ###################################################################################################################
    ###################################################################################################################
    def bayesianStats(df, dimension=3):
        df = df.dropna()

        wipeOffColumns = ['首次涨停时间',
                          '最后涨停时间',
                          'peak突破数/∑',
                          '1日开盘30分涨幅(%)'
                          ]

        columns = DySS_LimitUpAnalysis.colNames[2:]
        columns = [x for x in columns if x not in wipeOffColumns]

        pcaDf = df[columns]

        pca = PCA(n_components=dimension)
        pcaData = pca.fit_transform(pcaDf.values)

        # concat
        columns = list(df.columns)
        prefixColumns = columns[:columns.index('开盘比(%)')]
        postColumns = ['1日开盘30分涨幅(%)', '1日涨幅(%)']

        # pca DF
        pcaDf = pd.DataFrame(data=pcaData, columns=['pca%d'%x for x in range(dimension)])

        # orginal DF
        df = df.reset_index()
        del df['index']

        retDf = pd.concat([ df[prefixColumns], pcaDf, df[postColumns] ], axis=1)

        return retDf
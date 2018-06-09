from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_StrongBack(DyStockSelectStrategyTemplate):
    """ 升浪开始，回踩均线
    """
    name = 'DySS_StrongBack'
    chName = '强势股回踩'

    colNames = ['代码', '名称', '升浪日期区间', '升浪交易日数', '升浪涨幅(%)', '回踩交易日数', '回踩跌幅(%)', '回踩效率', '盘中跌破回踩均线']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('升浪涨幅不低于(%)', 25),
                    ('回踩高均线', 10),
                    ('回踩低均线', 20),
                    ('最小回踩周期', 2),
                    ('最大回踩周期', 7),
                    ('总周期', 17),
                    ('当日影线形态', 0),
                    ('当日阴线', 0),
                    ('当日回踩最低', 0),
                    ('升浪阳线结束', 0),
                    ('升浪结束影线形态', 0)
                ])

    paramToolTip = {'当日影线形态': '0：不考虑，1：长下影线并上影线不能长于下影线',
                    '当日回踩最低': '0：不考虑，1：当日的最低价是回调周期的最低价',
                    '升浪结束影线形态': '0：不考虑，1：升浪结束日不是长上影结束'
                    }


    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._risePct               = param['升浪涨幅不低于(%)']
        self._backHighMa            = param['回踩高均线']
        self._backLowMa             = param['回踩低均线']
        self._minBackDayNbr         = param['最小回踩周期']
        self._maxBackDayNbr         = param['最大回踩周期']
        self._totalDayNbr           = param['总周期']
        self._curShadowShape        = False if param['当日影线形态'] == 0 else True
        self._curNegativeLine       = False if param['当日阴线'] == 0 else True
        self._curBackLowest         = False if param['当日回踩最低'] == 0 else True
        self._riseEndPositveLine    = False if param['升浪阳线结束'] == 0 else True
        self._riseEndShadowShape    = False if param['升浪结束影线形态'] == 0 else True

        # for easy access
        self._periodNbr = self._totalDayNbr
        self._backHighMaName = 'ma%s'%self._backHighMa
        self._backLowMaName = 'ma%s'%self._backLowMa

    def onDaysLoad(self):
        return self._baseDate, -(self._periodNbr + max(self._backHighMa, self._backLowMa) - 2)

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes
        
        self._startDay = self._daysEngine.tDaysOffset(self._baseDate, -self._periodNbr + 1)
        self._endDay = self._daysEngine.tDaysOffset(self._baseDate, 0)

    def onStockDays(self, code, df):
        # save orginal DF
        orgDf = df

        # 计算5, @self._backMa日均线
        maDf = DyStockDataUtility.getMas(df, list(set([5, self._backHighMa, self._backLowMa])))
        df = df.ix[self._startDay:self._endDay]

        # 剔除周期内停牌的股票
        if maDf.shape[0] != self._periodNbr or df.shape[0] != self._periodNbr:
            return

        # 当日各个指标
        close = df.ix[self._endDay, 'close']
        low = df.ix[self._endDay, 'low']
        open = df.ix[self._endDay, 'open']
        high = df.ix[self._endDay, 'high']

        backHighMaValue = maDf.ix[self._endDay, self._backHighMaName]
        backLowMaValue = maDf.ix[self._endDay, self._backLowMaName]

        # 当日影线形态
        if self._curShadowShape:
            # 当日长下影线
            if not self._forTrade:
                if (close - low)/abs(close - open) <= 3: return

            # 当日上影线不能长于下影线
            if not self._forTrade:
                if (high - max(close, open)) > (min(close, open) - low): return

        # 当日阴线回踩
        if self._curNegativeLine:
            if close > open: return

        # 当日收盘价在回踩低均线上, 回踩高均线和回踩低均线均值下半区
        if not self._forTrade:
            if not((backHighMaValue + backLowMaValue)/2 > close >= backLowMaValue):
                return
        else:
            if not(backHighMaValue > close >= backLowMaValue):
                return

        # 盘中跌破回踩低均线，收盘在回踩低均线上
        isDownBackMa = '是' if low < backLowMaValue else '否'

        idxmax = df.ix[-self._maxBackDayNbr-1:, 'high'].idxmax() # 升浪区间结束日期
        idxmaxPos = df.index.get_loc(idxmax)

        maxHigh = df.ix[idxmaxPos, 'high']
        maxClose = df.ix[idxmaxPos, 'close']
        maxOpen = df.ix[idxmaxPos, 'open']

        # 升浪阳线结束
        if self._riseEndPositveLine:
            if maxClose <= maxOpen: return

        # 升浪不是长上影结束
        if self._riseEndShadowShape:
            if (maxHigh - maxClose)/(maxClose - maxOpen) > 3: return

        backDf = df.ix[idxmaxPos+1:]

        # 回调最低价是当日
        if self._curBackLowest:
            if low != backDf['low'].min(): return

        # 至少回调@self._minBackDayNbr日
        backDayNbr = backDf.shape[0]

        if not self._forTrade:
            if not(backDayNbr >= self._minBackDayNbr):
                return
        else:
            if not(backDayNbr >= self._minBackDayNbr - 1):
                return

        backPct = (maxHigh - low)*100/maxHigh

        # 回踩波动效率，以收盘价计算
        backEfficiencyRatio, backVolatilityRatio = DyStockDataUtility.getVolatilityEfficiencyRatio(df['close'][idxmaxPos:])

        # 当日波动不能超过总波动的一半
        if backVolatilityRatio[-1] > 0.5: return

        # 最近3日内没有触及跌停
        shiftCloses = df['close'].shift(1)
        pctChange = (df['low'] - shiftCloses)/shiftCloses
        backPctChange = pctChange[backDf.index]
        if (backPctChange[-3:] < -0.095).any():
            return

        # 是不是从最大值回调
        riseDf = df.ix[self._startDay:idxmax] # 假设的升浪DF

        if idxmax != riseDf['high'].idxmax():
            return

        # 5日均线上的连续涨幅不低于@self._risePct
        idxmin = (riseDf['close'] > maDf.ix[self._startDay:idxmax, 'ma5']).iloc[::-1].idxmin() # 找到连续在5日线上的交易日

        minLow = riseDf.ix[idxmin, 'low']

        risePct = (maxHigh - minLow)*100/minLow
        if risePct < self._risePct:
            return

        # 升浪交易日区间
        riseDf = df.ix[idxmin:idxmax]

        maxRiseVol = riseDf['volume'].max()

        # ---------- 成交量 ----------

        # 不是阴线巨量见顶
        if maxClose < maxOpen:
            if df.ix[idxmax, 'volume'] > riseDf.ix[:-1, 'volume'].mean()*1.5:
                return

        idxmaxVol = backDf['volume'].idxmax()
        idxmaxVolPos = backDf.index.get_loc(idxmaxVol)

        maxBackVol = backDf.ix[idxmaxVolPos, 'volume']

        # 回踩期间日最大成交量小于升浪期间日最大交易量
        if maxBackVol >= maxRiseVol:
            return

        # 当日不是最大回调单日成交量，也就是说不是放量下跌的开始
        meanBackVol = backDf.ix[:idxmaxVolPos, 'volume'].mean() # 回调过程中最大单日成交量之前的成交量均值

        if idxmaxVol.strftime("%Y-%m-%d") == self._endDay and maxBackVol/meanBackVol > 2:
            return

        if self._forTrade:
            assert(not backDf.empty)
            meanBackVol = int(backDf['volume'].mean()) # 所有回调日的成交量均值
            maxRiseVol = int(maxRiseVol)

        riseDates = [riseDf.index[0].strftime("%Y-%m-%d"), riseDf.index[-1].strftime("%Y-%m-%d")]
        riseDayNbr = riseDf.shape[0]

        # 设置结果
        group = [code, self._stockAllCodes[code], ','.join(riseDates), riseDayNbr, risePct, backDayNbr, backPct, backEfficiencyRatio, isDownBackMa]
        self._result.append(group)

        # 设置实盘结果
        if self._forTrade:
            self._resultForTrade['date'] = self._endDay
            self._resultForTrade['backHighMa'] = self._backHighMa
            self._resultForTrade['backLowMa'] = self._backLowMa
            self._resultForTrade['stocks'][code] = dict(maxRiseVol=maxRiseVol, meanBackVol=meanBackVol)
            self._resultForTrade['stocks'][code]['closes'] = orgDf['close'][-self._backLowMa+1:].values.tolist()

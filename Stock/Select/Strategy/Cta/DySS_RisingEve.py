import operator

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_RisingEve(DyStockSelectStrategyTemplate):
    name = 'DySS_RisingEve'
    chName = '上涨前夕'

    colNames = ['代码', '名称', '斜率之差']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 5),
                    ('N日收盘高于五日均线', 5),
                    ('选几只股票', 50)
                ])

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._forwardNTDays         = param['向前N日周期']
        self._nTDays                = param['N日收盘高于五日均线']
        self._selectStockNbr        = param['选几只股票']

    def onDaysLoad(self):
        return self._baseDate, -self._forwardNTDays + 1 - 4

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes
        
        self._startDay = self._daysEngine.tDaysOffset(self._baseDate, -self._forwardNTDays + 1)
        self._endDay = self._daysEngine.tDaysOffset(self._baseDate, 0)


        self._indexesPctChangeSeries = {}
        self._indexesMaDf = {}

    def onIndexDays(self, code, df):
        
        self._indexesPctChangeSeries[code] = df['close'].pct_change()
        
        self._indexesMaDf[code] = DyStockDataUtility.getMas(df, [5])

    def onStockDays(self, code, df):
        if 0:
            pctChangeSeries = df['close'].pct_change()

        # 计算五日均线
        maDf = DyStockDataUtility.getMas(df, [5])

        df = df.ix[maDf.index] # 以均线数据对齐

        # 收盘高于五日均线的交易日不小于@self._nTDays
        if 0:
            if (df['close'] >= maDf['ma5']).sum() < self._nTDays:
                return

        # 阳线交易日不小于@self._nTDays
        if 0:
            if (df['close'] >= df['open']).sum() < self._nTDays:
                return

        # 比指数强
        if 0:
            indexPctChangeSeries = self._indexesPctChangeSeries[self._daysEngine.getIndex(code)][maDf.index]
            pctChangeSeries = pctChangeSeries[maDf.index]
            if (pctChangeSeries - indexPctChangeSeries).sum() < 0.01 * self._nTDays:
                return

        # 剔除一字板涨停
        if (df['high'] == df['low']).sum() > 2:
            return

        # 五日均线斜率不小于1
        if 0:
            if (maDf.ix[-1, 'ma5'] - maDf.ix[0, 'ma5'])/4 < 0.6:
                return

        # 股票指数斜率差
        stockSlope = (maDf.ix[-1, 'ma5'] - maDf.ix[0, 'ma5'])/(4 * maDf.ix[1, 'ma5'])

        indexMaDf = self._indexesMaDf[self._daysEngine.getIndex(code)].ix[maDf.index]
        indexSlope = (indexMaDf.ix[-1, 'ma5'] - indexMaDf.ix[0, 'ma5'])/(4 * indexMaDf.ix[1, 'ma5'])

        if (stockSlope - indexSlope)*100 < 0.15:
            return

        # 设置结果
        pair = [code, self._stockAllCodes[code], (stockSlope - indexSlope)*100]
        self._result.append(pair)
        self._result.sort(key = operator.itemgetter(2), reverse = True)
        self._result = self._result[:self._selectStockNbr]

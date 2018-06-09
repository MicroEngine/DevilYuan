from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_AbnormalVolatility(DyStockSelectStrategyTemplate):
    name = 'DySS_AbnormalVolatility'
    chName = '异常波动'

    colNames = ['代码', '名称', '最高自身波动z-score', '收盘自身波动z-score', '最低自身波动z-score']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 30),
                    ('最高自身波动>=(%)', 4),
                    ('收盘自身波动>=(%)', 4),
                    ('最低自身波动>=(%)', -1)
                ])

    #autoFillDays = True
    continuousTicks = True

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._forwardNDays          = param['向前N日周期']
        self._highSelfVolatility    = param['最高自身波动>=(%)']
        self._closeSelfVolatility   = param['收盘自身波动>=(%)']
        self._lowSelfVolatility     = param['最低自身波动>=(%)']

    def onDaysLoad(self):
        return self._baseDate, -self._forwardNDays - 1

    def onTicksLoad(self):
        return self._baseDate, 0

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes
        
        self._indexVolatility = {}

    def onIndexDays(self, code, df):
        indexHighAbsoluteVolatility = (df['high'] - df['close'].shift(1))/df['close'].shift(1)
        indexCloseAbsoluteVolatility = (df['close'] - df['close'].shift(1))/df['close'].shift(1)
        indexLowAbsoluteVolatility = (df['low'] - df['close'].shift(1))/df['close'].shift(1)

        if code not in self._indexVolatility:
            self._indexVolatility[code] = {'high': indexHighAbsoluteVolatility,
                                           'close': indexCloseAbsoluteVolatility,
                                           'low': indexLowAbsoluteVolatility
                                           }

    def onStockDays(self, code, df):
        if df.shape[0] != self._forwardNDays + 2:
            return

        indexCode = self._daysEngine.getIndex(code)

        stockHighAbsoluteVolatility = (df['high'] - df['close'].shift(1))/df['close'].shift(1)
        stockCloseAbsoluteVolatility = (df['close'] - df['close'].shift(1))/df['close'].shift(1)
        stockLowAbsoluteVolatility = (df['low'] - df['close'].shift(1))/df['close'].shift(1)

        stockHighSelfVolatility = stockHighAbsoluteVolatility - self._indexVolatility[indexCode]['high']
        stockCloseSelfVolatility = stockCloseAbsoluteVolatility - self._indexVolatility[indexCode]['close']
        stockLowSelfVolatility = stockLowAbsoluteVolatility - self._indexVolatility[indexCode]['low']

        volatilityDf = pd.concat([stockHighSelfVolatility,
                                  stockCloseSelfVolatility,
                                  stockLowSelfVolatility
                                 ], axis=1)

        # exclude @baseDate
        oldDf = volatilityDf.ix[:-1]

        # 计算基准日期的对应的z-score
        stds = oldDf.std()
        means = oldDf.mean()

        zscores = (volatilityDf.ix[-1].values - means.values)/stds.values

        if zscores[0] >= self._highSelfVolatility and zscores[1] >= self._closeSelfVolatility and zscores[2] >= self._lowSelfVolatility:
            # 设置结果
            group = [code, self._stockAllCodes[code], zscores[0], zscores[1], zscores[2]]
            self._result.append(group)

    def _getLatestLimitUpTime(self, df):
        highest = df['price'].max()
        lowest = df['price'].min()

        if highest == lowest:
            return df.index[0].strftime('%H:%M:%S'), True

        idxmin = (df['price'] == highest).iloc[::-1].idxmin()

        return idxmin.strftime('%H:%M:%S'), False

    def onStockTicks(self, code, dfs):
        limitUpTime, oneWord = self._getLatestLimitUpTime(dfs)

        if limitUpTime > '14:30:00' or oneWord:
            self.removeFromResult(code)

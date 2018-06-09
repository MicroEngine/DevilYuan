import operator

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_Stagflation(DyStockSelectStrategyTemplate):
    name = 'DySS_Stagflation'
    chName = '滞涨'

    colNames = ['代码', '名称', '现价最低比(%)', '最大跌幅(%)', '现价60日均线比(%)']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 30),
                    ('选几只股票', 50)
                ])

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._forwardNTDays         = param['向前N日周期']
        self._selectStockNbr        = param['选几只股票']

    def onDaysLoad(self):
        return self._baseDate, -max(self._forwardNTDays, 60) + 1

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes
        
        self._startDay = self._daysEngine.tDaysOffset(self._baseDate, -self._forwardNTDays + 1)
        self._endDay = self._daysEngine.tDaysOffset(self._baseDate, 0)

    def onStockDays(self, code, df):
        # 计算60日均线
        maDf = DyStockDataUtility.getMas(df, [60])
        df = df.ix[self._startDay:self._endDay]

        ma60 = maDf.ix[self._endDay, 'ma60']
        close = df.ix[self._endDay, 'close']

        low = df['low'].min()

        # 最低价在最高价的右侧
        lowDay = df['low'].idxmin()
        high = df.ix[self._startDay:lowDay, 'high'].max()

        closeLowRatio = (close - low)*100/low
        maxDropRatio = (high - low)*100/high
        closeM60Ration = (close - ma60)*100/ma60

        # 设置结果
        pair = [code, self._stockAllCodes[code], closeLowRatio, maxDropRatio, closeM60Ration]
        self._result.append(pair)
        self._result.sort(key=operator.itemgetter(2))
        self._result = self._result[:self._selectStockNbr]

import operator

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_LimitUpRise(DyStockSelectStrategyTemplate):
    name = 'DySS_LimitUpRise'
    chName = '板后小阳'

    colNames = ['代码', '名称', '涨幅(%)']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d"))
                ])

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']

    def onDaysLoad(self):
        return self._baseDate, -30

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes
        
        #self._startDay = self._daysEngine.tDaysOffset(self._baseDate, -1)
        #self._endDay = self._daysEngine.tDaysOffset(self._baseDate, 0)

    def onStockDays(self, code, df):
        closePctChange = df['close'].pct_change().dropna()
        if closePctChange.shape[0] != 30: return

        if closePctChange[-2] < DyStockCommon.limitUpPct/100: return
        if closePctChange[-1] <= 0: return

        if (closePctChange >= DyStockCommon.limitUpPct/100).sum() > 1: return

        if df.ix[-1, 'turn']/df.ix[-2, 'turn'] >= 2: return

        # 设置结果
        pair = [code, self._stockAllCodes[code], closePctChange[-1]*100]
        self._result.append(pair)

        # 设置实盘结果
        if self._forTrade:
            self._resultForTrade['stocks'] = None

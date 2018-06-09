import operator

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_MaWalk(DyStockSelectStrategyTemplate):
    name = 'DySS_MaWalk'
    chName = '均线游走'

    autoFillDays = True
    optimizeAutoFillDays = True

    colNames = ['代码', '名称']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('游走均线', 20),
                    ('游走均线之上日数', 3),
                    ('均线多头排列', '20,30,60'),
                ])


    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._walkMa                = param['游走均线']
        self._walkMaUpDayNbr        = param['游走均线之上日数']
        self._longMas               = [int(x) for x in param['均线多头排列'].split(',')]; self._longMas.sort()

    def onDaysLoad(self):
        return self._baseDate, -max(self._longMas[-1], self._walkMa) - self._walkMaUpDayNbr

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes

    def onStockDays(self, code, df):
        maDf = DyStockDataUtility.getMas(df, set([self._walkMa] + self._longMas))
        df = df.ix[maDf.index]

        if df.shape[0] <= self._walkMaUpDayNbr:
            return

        # 最低价在均线之上
        lows = df.ix[-self._walkMaUpDayNbr-1:-1, 'low']
        mas = maDf.ix[-self._walkMaUpDayNbr-1:-1, 'ma%s'%self._walkMa]
        if (lows < mas).sum() > 0:
            return

        # 当日下穿均线
        close = df.ix[-1, 'close']
        low = df.ix[-1, 'low']
        ma = maDf.ix[-1, 'ma%d'%self._walkMa]

        if not(low <= ma and close > ma):
            return

        # 当日均线多头排列
        preMaDiff = None
        for i in range(len(self._longMas) - 1):
            ma = maDf.ix[-1, 'ma%s'%self._longMas[i]]
            nextMa = maDf.ix[-1, 'ma%s'%self._longMas[i+1]]

            if ma < nextMa:
                return

            maDiff = ma - nextMa
            if preMaDiff is not None:
                if preMaDiff > maDiff:
                    return

            preMaDiff = maDiff

        # 设置结果
        group = [code, self._stockAllCodes[code]]
        self._result.append(group)

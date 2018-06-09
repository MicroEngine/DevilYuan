import operator

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_InsideRedLine(DyStockSelectStrategyTemplate):
    name = 'DySS_InsideRedLine'
    chName = '阳线包含'

    autoFillDays = True
    optimizeAutoFillDays = True

    colNames = ['代码', '名称']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('连续阴线数', 3),
                ])


    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate                  = param['基准日期']
        self._consecutiveGreenLineNbr   = param['连续阴线数']

    def onDaysLoad(self):
        return self._baseDate, -self._consecutiveGreenLineNbr-1

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes

    def onStockDays(self, code, df):
        increases = df['close'].pct_change()*100

        if increases[-self._consecutiveGreenLineNbr-1] < 7:
            return

        low = df['low'][-self._consecutiveGreenLineNbr-1]

        volumes = df['volume']
        for i in range(-self._consecutiveGreenLineNbr-1, -1):
            if volumes[i] < volumes[i+1]:
                return

        if df['low'][-self._consecutiveGreenLineNbr:].min() < low:
            return

        highs = df['high']
        if highs[-self._consecutiveGreenLineNbr-1:-self._consecutiveGreenLineNbr+1].max() != highs[-self._consecutiveGreenLineNbr-1:].max():
            return

        # 设置结果
        group = [code, self._stockAllCodes[code]]
        self._result.append(group)

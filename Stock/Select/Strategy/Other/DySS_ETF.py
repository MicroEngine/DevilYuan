from ..DyStockSelectStrategyTemplate import *
from ....Common.DyStockCommon import *


class DySS_ETF(DyStockSelectStrategyTemplate):
    name = 'DySS_ETF'
    chName = 'ETF'

    colNames = ['代码', '名称']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                ])

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._isRun                 = False

    def onCodes(self):
        return [DyStockCommon.etf50, DyStockCommon.etf300, DyStockCommon.etf500]

    def onDaysLoad(self):
        return self._baseDate, 0

    def onIndexDays(self, code, df):
        if self._isRun:
            return

        for code in [DyStockCommon.etf50, DyStockCommon.etf300, DyStockCommon.etf500]:
            pair = [code, DyStockCommon.funds[code]]
            self._result.append(pair)

        self._isRun = True

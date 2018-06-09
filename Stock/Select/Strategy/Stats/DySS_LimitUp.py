from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_LimitUp(DyStockSelectStrategyTemplate):
    name = 'DySS_LimitUp'
    chName = '连板'

    colNames = ['代码', '名称', '连板数']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('最大连板数', 7)
                ])

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._maxLimitUpNbr         = param['最大连板数']

    def onDaysLoad(self):
        return self._baseDate, -self._maxLimitUpNbr

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes
        
        #self._startDay = self._daysEngine.tDaysOffset(self._baseDate, -1)
        #self._endDay = self._daysEngine.tDaysOffset(self._baseDate, 0)

    def onStockDays(self, code, df):
        closePctChange = df['close'].pct_change().dropna()

        # 剔除停牌或者新股
        if closePctChange.shape[0] < self._maxLimitUpNbr:
            return

        limitUpBool = closePctChange >= DyStockCommon.limitUpPct/100
        limitUpNbr = int(limitUpBool.sum())
        if limitUpNbr == 0:
            return

        # 剔除一字板涨停
        limitUpDf = df[1:][limitUpBool]
        if limitUpDf[limitUpDf['high'] == limitUpDf['low']].shape[0] == limitUpDf.shape[0]:
            return

        # 设置结果
        pair = [code, self._stockAllCodes[code], limitUpNbr]
        self._result.append(pair)

import operator

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_Rebound(DyStockSelectStrategyTemplate):
    name = 'DySS_Rebound'
    chName = '反弹'

    colNames = ['代码', '名称', '效率系数', '当日跌幅占比']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d"))
                ])

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']

    def onDaysLoad(self):
        return self._baseDate, -5

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes
        
    def onStockDays(self, code, df):
        # 剔除周期内停牌的股票
        if df.shape[0] != 6:
            return

        # 剔除当日收盘价等于最低价，意味着收盘肯定不是跌停
        if df.ix[-1, 'close'] == df.ix[-1, 'low']: return

        # 下降趋势
        direction = df.ix[-1, 'close'] - df.ix[0, 'close']
        if direction > 0: return

        # 绝对波动
        closes = df['close']
        change = closes - closes.shift(1)
        volatility = abs(change).sum()

        #　效率系数
        efficiencyRatio = direction/volatility

        if efficiencyRatio > -0.8: return

        curDropRatio = abs(change[-1])/abs(direction)
        if curDropRatio > 0.5: return

        # 设置结果
        pair = [code, self._stockAllCodes[code], efficiencyRatio, curDropRatio]
        self._result.append(pair)
        self._result.sort(key=operator.itemgetter(2), reverse=False)

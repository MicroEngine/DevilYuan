import operator

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_OverSold(DyStockSelectStrategyTemplate):
    """ 升浪开始，回踩均线
        升浪以收盘在5日均线上
        升浪统计10日，回踩统计5日
    """
    name = 'DySS_OverSold'
    chName = '超卖'

    colNames = ['代码', '名称', '收盘五日均线比', '最低五日均线比']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('选几只股票', 20)
                ])

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._selectStockNbr        = param['选几只股票']

    def onDaysLoad(self):
        return self._baseDate, -4

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes

        self._endDay = self._daysEngine.tDaysOffset(self._baseDate, 0)
        
    def onStockDays(self, code, df):
        # 计算5, @self._backMa日均线
        maDf = DyStockDataUtility.getMas(df, [5])
        df = df.ix[-1:]

        ma5 = maDf.ix[0, 'ma5']

        close = df.ix[0, 'close']
        low = df.ix[0, 'low']

        # 设置结果
        pair = [code, self._stockAllCodes[code], close/ma5, low/ma5]
        self._result.append(pair)
        self._result.sort(key = operator.itemgetter(2))
        self._result = self._result[:self._selectStockNbr]

        # 设置实盘结果
        if self._forTrade:
            self._resultForTrade['date'] = self._endDay

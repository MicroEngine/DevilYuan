import operator

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_HighTurn(DyStockSelectStrategyTemplate):
    name = 'DySS_HighTurn'
    chName = '高换手'

    autoFillDays = True
    optimizeAutoFillDays = True

    colNames = ['代码', '名称', '排名', '换手率(%)', '成交额(亿)', '流通股本(亿股)', '昨日换手率(%)']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('选几只股票', 100)
                ])


    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._selectStockNbr        = param['选几只股票']

        self.__data = {}

    def onDaysLoad(self):
        return self._baseDate, -1

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes

    def onStockDays(self, code, df):
        turn = df.ix[-1, 'turn']
        amt = df.ix[-1, 'amt']/10**8
        volume = df.ix[-1, 'volume']
        preTurn = df.ix[-2, 'turn']

        float = volume/turn*100/10**8

        self.__data[code] = [self._stockAllCodes[code], turn, amt, float, preTurn]

    def onDone(self):
        df = pd.DataFrame(self.__data).T
        start = self.colNames.index('换手率(%)')
        df.rename(columns={i: x for i, x in enumerate(['名称'] + self.colNames[start:])}, inplace=True)

        series = df['换手率(%)'].rank(ascending=False)
        rankSeries = series

        series = df['成交额(亿)'].rank(ascending=False)
        rankSeries += series

        # 流通股本越大越好，这样对相对的换手率形成制约。盘子越大的股票，意味着大资金关注多，一般认为大资金是聪明钱。
        series = df['流通股本(亿股)'].rank(ascending=False)
        rankSeries += series

        rankSeries = rankSeries.rank()
        rankSeries.name = '排名'

        df = pd.concat([rankSeries, df], axis=1)
        df.sort_values('排名', ascending=True, inplace=True)

        # set result
        if self._selectStockNbr > 0:
            df = df.ix[:self._selectStockNbr]

        df = df.reindex(columns=self.colNames[1:])
        df.reset_index(inplace=True)

        self._result = df.values.tolist()

        
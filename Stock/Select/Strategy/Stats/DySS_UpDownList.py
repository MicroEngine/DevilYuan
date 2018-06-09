import operator

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_UpDownList(DyStockSelectStrategyTemplate):
    name = 'DySS_UpDownList'
    chName = '涨跌幅榜'

    colNames = ['代码', '名称', None, '波动效率']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 30),
                    ('涨跌', 1),
                    ('选几只股票', 200)
                ])

    paramToolTip = {'涨跌': '1: 涨, 0: 跌'}


    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._forwardNTDays         = param['向前N日周期']
        self._upDown                = False if param['涨跌'] == 0 else True
        self._selectStockNbr        = param['选几只股票']

        self.colNames[2] = '前{0}日{1}幅(%)'.format(self._forwardNTDays, '涨' if self._upDown else '跌')

    def onDaysLoad(self):
        return self._baseDate, -self._forwardNTDays

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes
        
    def onStockDays(self, code, df):
        # 剔除最前3日一字板, 新股首日涨幅剔除
        dayNbr = min(4, self._forwardNTDays)
        dayNbr_ = 0
        for i in range(1, dayNbr):
            if df.ix[i, 'high'] != df.ix[i, 'low']: break
            dayNbr_ += 1

        if dayNbr - 1 == dayNbr_: return

        # 涨幅
        pct = (df.ix[-1, 'close'] - df.ix[0, 'close'])*100/df.ix[0, 'close']

        efficiencyRatio, _ = DyStockDataUtility.getVolatilityEfficiencyRatio(df['close'])

        # 设置结果
        pair = [code, self._stockAllCodes[code], pct, efficiencyRatio]
        self._result.append(pair)
        self._result.sort(key=operator.itemgetter(2), reverse=self._upDown)
        self._result = self._result[:self._selectStockNbr]

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_NeedleBottom(DyStockSelectStrategyTemplate):
    name = 'DySS_NeedleBottom'
    chName = '单针探底'

    colNames = ['代码', '名称', '下影占比(%)']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 15),
                    ('周期内跌幅至少(%)', 20),
                    ('下影占比至少(%)', 61.8)
                ])

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._forwardNTDays         = param['向前N日周期'] # @self._baseDate is included
        self._dropDownPct           = param['周期内跌幅至少(%)']
        self._needleBottomRatio     = param['下影占比至少(%)']

    def onDaysLoad(self):
        return self._baseDate, -max(self._forwardNTDays, 5) + 1

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes
        
        self._startDay = self._daysEngine.tDaysOffset(self._baseDate, -self._forwardNTDays + 1)
        self._endDay = self._daysEngine.tDaysOffset(self._baseDate)

    def onStockDays(self, code, df):
        # 计算5日均线
        maDf = DyStockDataUtility.getMas(df, [5])
        df = df.ix[self._startDay:self._endDay]

        # 剔除周期内停牌的股票
        if df.shape[0] != self._forwardNTDays:
            return

        close = df.ix[self._endDay, 'close']
        low = df.ix[self._endDay, 'low']
        open = df.ix[self._endDay, 'open']
        high = df.ix[self._endDay, 'high']

        highest = df['high'].max()
        lowest = df['low'].min()

        if lowest != low: return

        if low == high: return

        if close >= maDf.ix[self._endDay, 'ma5']: return

        #if close < open: return

        if (highest - lowest)*100/highest < self._dropDownPct: return

        # 当日下影占比
        if not self._forTrade:
            needleBottomRatio = (min(close, open) - low)*100 / (high - low)
            if needleBottomRatio < self._needleBottomRatio: return

        # 设置结果
        if not self._forTrade:
            pair = [code, self._stockAllCodes[code], needleBottomRatio]
            self._result.append(pair)

        # 设置实盘结果
        if self._forTrade:
            self._resultForTrade['stocks'][code] = None

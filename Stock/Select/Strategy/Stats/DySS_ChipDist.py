from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_ChipDist(DyStockSelectStrategyTemplate):
    """
        筹码分布
    """
    name = 'DySS_ChipDist'
    chName = '筹码分布'

    autoFillDays = True
    optimizeAutoFillDays = True
    continuousTicks = True

    colNames = ['代码', '名称',
                '下上筹码比',
                '下筹码/20日成交量均值',
                '短期下上筹码比',
                '短期最高价跌幅(%)'
                ]

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 120),
                    ('筹码k值', 10),
                    ('短期N日周期', 30),
                    ('选几只股票', 50)
                ])

    paramToolTip = {'筹码k值': '统计当前价格+/-k%范围内的筹码',
                    }

    # 策略私有参数


    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._forwardNTDays         = param['向前N日周期']
        self._k                     = param['筹码k值']
        self._shortNTDays           = param['短期N日周期']
        self._selectStockNbr        = param['选几只股票']

    def onDaysLoad(self):
        return self._baseDate, -self._forwardNTDays + 1

    def onTicksLoad(self):
        return self._baseDate, -self._shortNTDays + 1

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine
        self._ticksEngine = errorDataEngine.ticksEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes

        self._priceData = {} # {code: [close, high price of short period]}

    ###################################################################################################################
    ###################################################################################################################
    def onStockDays(self, code, df):
        close = df.ix[-1, 'close']
        diff = close*self._k/100
        up, down = close + diff, close - diff

        s = DyStockDataUtility.getChipDistByDays(df, ohlcRatio=40, gridNbr=60)

        downVolume = s[down:close].sum()
        upVolume = s[close:up].sum()
        downUpRatio = downVolume/upVolume

        mean20Volume = df['volume'][-20:].mean()
        downMean20Ratio = downVolume/mean20Volume

        # save
        self._priceData[code] = [close, df['high'][-self._shortNTDays:].max()]

        # 设置结果
        row = [code, self._stockAllCodes[code],
               downUpRatio,
               downMean20Ratio
               ]
        self._result.append(row)
        self._result.sort(key=operator.itemgetter(2), reverse=True)
        self._result = self._result[:self._selectStockNbr]

    def onStockTicks(self, code, dfs):
        close, high = self._priceData.get(code)
        diff = high - close
        up, down = close + diff, close - diff

        s = DyStockDataUtility.getChipDistByTicks(dfs)

        ratio = s[down:close].sum()/s[close:up].sum()

        # 设置结果
        partRow = [ratio,
                   (high - close)/high*100
                   ]

        row = self.getFromResult(code)
        row.extend(partRow)

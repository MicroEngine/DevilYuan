from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_Correlation(DyStockSelectStrategyTemplate):
    name = 'DySS_Correlation'
    chName = '相关性'

    colNames = ['代码', '名称', '键值']

    param = OrderedDict\
                ([
                    ('跟哪个标的比较', '指数'),
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 30),
                    ('收盘价相关性权重', 100),
                    ('收盘价相关系数', 1), # 1：正相关，-1：负相关
                    ('收盘价相对强弱权重', 0),
                    ('收盘价相对系数', 1), # 1：相对强，-1：相对弱
                    ('选几只股票', 100)
                ])

    # 策略右键Item菜单和操作
    def scatterAct(dataViewer, param, code):
        dataViewer.plotScatterChart(param['跟哪个标的比较'], code, param['基准日期'], -param['向前N日周期'] + 1)

    itemMenu = OrderedDict\
                ([
                    ('散列图', scatterAct),
                ])


    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._target                = param['跟哪个标的比较']
        self._baseDate              = param['基准日期']
        self._forwardNTDays         = param['向前N日周期']
        self._closeCorrWeight       = param['收盘价相关性权重']
        self._closeCorr             = param['收盘价相关系数']
        self._closeStrongWeight     = param['收盘价相对强弱权重']
        self._closeStrong           = param['收盘价相对系数']
        self._selectStockNbr        = param['选几只股票']

    def onDaysLoad(self):
        return self._baseDate, -self._forwardNTDays

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes
        
        self._startDay = self._daysEngine.tDaysOffset(self._baseDate, -self._forwardNTDays)
        self._endDay = self._daysEngine.tDaysOffset(self._baseDate, 0)

        # get target DF
        if self._target != '指数':
            self._targetCode = self._daysEngine.getCode(self._target)

            self._targetClose = self._daysEngine.getDataFrame(self._targetCode, self._startDay, self._endDay)['close']
            self._targetCloseChange = self._targetClose.pct_change()
        else:
            self._targetCode = None

            self._targetClose = {}
            self._targetCloseChange = {}

    def onIndexDays(self, code, df):
        if self._target != '指数': return

        self._targetClose[code] = df['close']
        self._targetCloseChange[code] = self._targetClose[code].pct_change()

    def _corr(self, code, df):
        if code == self._targetCode: return None

        if self._target == '指数':
            targetClose = self._targetClose[self._daysEngine.getIndex(code)]
        else:
            targetClose = self._targetClose

        # 至少需要80%的日期，股票停牌和刚上市没啥意义
        if df.shape[0]/targetClose.shape[0] < 0.8: return None

        corr = targetClose.corr(df['close'])

        return corr

    def _strong(self, code, df):
        if code == self._targetCode: return None

        if self._target == '指数':
            targetCloseChange = self._targetCloseChange[self._daysEngine.getIndex(code)]
        else:
            targetCloseChange = self._targetCloseChange

        close = df['close'].pct_change()
        mean = (close - targetCloseChange).mean()
        mean *= 100

        mean /= 20 # 标准化, 股票振幅10%, 所以两只股票的最大振幅差是20%

        return mean

    def onStockDays(self, code, df):
        try:
            corr = self._corr(code, df)
            if corr is None: return
            
            strong = self._strong(code, df)
            if strong is None: return

            key = ( corr * self._closeCorrWeight * self._closeCorr + \
                    strong * self._closeStrongWeight * self._closeStrong ) / 100

        except Exception as ex:
            return

        # 设置结果
        pair = [code, self._stockAllCodes[code], key]
        self._result.append(pair)
        self._result.sort(key=operator.itemgetter(2), reverse=True)
        self._result = self._result[:self._selectStockNbr]

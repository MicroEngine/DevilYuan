from statsmodels.tsa import stattools
import pandas as pd

from ..DyStockSelectStrategyTemplate import *


class DySS_Pairs(DyStockSelectStrategyTemplate):
    name = 'DySS_Pairs'
    chName = '配对'

    colNames = ['代码', '名称', 'p值(‰)']

    param = OrderedDict\
                ([
                    ('标的', '贵州茅台'),
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 500),
                    ('选几只股票', 200)
                ])

    # 策略右键Item菜单和操作
    def scatterChartAct(dataViewer, param, code):
        dataViewer.plotScatterChart(param['标的'], code, param['基准日期'], -param['向前N日周期'] + 1)

    def spreadChartAct(dataViewer, param, code):
        dataViewer.plotSpreadChart(param['标的'], code, param['基准日期'], -param['向前N日周期'] + 1)

    itemMenu = OrderedDict\
                ([
                    ('散列图', scatterChartAct),
                    ('价差图', spreadChartAct),
                ])


    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._target                = param['标的']
        self._baseDate              = param['基准日期']
        self._forwardNTDays         = param['向前N日周期']
        self._selectStockNbr        = param['选几只股票']

    def onDaysLoad(self):
        return self._baseDate, -self._forwardNTDays + 1

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine
        self._stockAllCodes = self._daysEngine.stockAllCodes
        
        # get target DF
        self._targetCode = self._daysEngine.getCode(self._target)
        self._targetDf = self._daysEngine.getDataFrame(self._targetCode)
        self._targetCloses = self._targetDf['close']
        self._targetDates = {x.strftime("%Y-%m-%d") for x in list(self._targetDf.index)}

    def onIndexDays(self, code, df):
        pass

    def _adfTest(self, s):
        """
            ADF Test
            p值越大：随机漫步，可能是趋势
            p值越小：均值回归
        """
        result = stattools.adfuller(s, 1)

        return result[1]

    def _spread(self, code, df):
        if code == self._targetCode:
            return None

        # 取交集日期
        dates = list(df.index)
        dates = {x.strftime("%Y-%m-%d") for x in dates}

        dates &= self._targetDates
        if len(dates)/self._forwardNTDays < 0.7:
            return None

        dates = sorted(list(dates))

        # create pandas time index
        dates = pd.DatetimeIndex(dates)

        # 标准化
        targetCloses = self._targetCloses[dates]
        targetCloses = np.log(targetCloses)
        targetCloses -= targetCloses[0]

        closes = df.ix[dates, 'close']
        closes = np.log(closes)
        closes -= closes[0]

        # spread
        spreads = targetCloses - closes

        # 平稳性检验
        pvalue = self._adfTest(spreads)

        return pvalue

    def onStockDays(self, code, df):
        pvalue = self._spread(code, df)
        if pvalue is None:
            return

        # 设置结果
        row = [code, self._stockAllCodes[code], pvalue*1000]
        self._result.append(row)
        self._result.sort(key=operator.itemgetter(2))
        self._result = self._result[:self._selectStockNbr]


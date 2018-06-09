import operator

from DyCommon.DyCommon import *
from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_SwingTrough(DyStockSelectStrategyTemplate):
    name = 'DySS_SwingTrough'
    chName = '波谷'

    autoFillDays = True
    optimizeAutoFillDays = True

    colNames = ['代码', '名称', '波谷跌幅(%)', '成交量比']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('跌幅(%)>=', 20),
                    ('成交量比>=', 3),
                ])

    paramToolTip = {'跌幅(%)>=': '最近波段高点到当前的整体跌幅',
                    '成交量比>=': '当日成交量跟前一日的比',
                    }

    # 策略参数
    feedDaysNbr = 60 # 为了找Swing


    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._dropDownRatio         = param['跌幅(%)>=']
        self._volumeRatio           = param['成交量比>=']
        #self._volatilityRatio       = param['波动率比>=']

    def onDaysLoad(self):
        return self._baseDate, -self.feedDaysNbr

    def onInit(self, dataEngine, errorDataEngine):
        self._daysEngine = dataEngine.daysEngine

        self._stockAllCodes = self._daysEngine.stockAllCodes

    def _getVolatility(self, df):
        trueVolatility = DyStockDataUtility.getVolatility(df)

        volumeRatios = df['volume']/df['volume'].shift(1)
        combinedVolatility = trueVolatility*np.sqrt(volumeRatios)

        return combinedVolatility

    def _checkVolatility(self, df):
        volatility = self._getVolatility(df)

        volatilityRatio = volatility[-1]/volatility[-2]
        if volatilityRatio < self._volatilityRatio:
            return False, volatilityRatio

        return True, volatilityRatio

    def _checkDropDown(self, df):
        extremas, peaks, bottoms = DyStockDataUtility.swings(df, w=4)

        peak = peaks[-1]
        low = df['low'][-1]

        ratio = (peak - low)/peak*100

        if ratio < self._dropDownRatio:
            return False, ratio

        return True, ratio

    def _checkVolume(self, df):
        volumes = df['volume']
        ratio = volumes[-1]/volumes[-2]

        if ratio < self._volumeRatio:
            return False, ratio

        return True, ratio
        
    def onStockDays(self, code, df):
        ret, volumeRatio = self._checkVolume(df)
        if not ret:
            return

        ret, dropDownRatio = self._checkDropDown(df)
        if not ret:
            return

        # 设置结果
        pair = [code, self._stockAllCodes[code], dropDownRatio, volumeRatio]
        self._result.append(pair)


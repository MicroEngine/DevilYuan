import math, operator

import talib

from ..DyStockSelectStrategyTemplate import *
from ....Data.Utility.DyStockDataUtility import *


class DySS_MacdBottomDeviation(DyStockSelectStrategyTemplate):
    name = 'DySS_MacdBottomDeviation'
    chName = 'MACD底背离'

    colNames = ['代码', '名称', '背离强度']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('MACD指标', 'close'),
                    ('极值窗口', 4),
                    ('底背离次数', 3),
                    ('金叉', 1)
                ])

    paramToolTip = {'MACD指标': 'open, high, low, close',
                    '极值窗口': '滑动窗口大小(w), 周期则为2w+1',
                    '金叉': '1：考虑金叉，0：不考虑金叉'
                    }

    autoFillDays = True

    # 策略参数
    macdDays = 100

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._macdIndicator         = param['MACD指标']
        self._extremaWindow         = param['极值窗口']
        self._bottomDeviationNbr    = param['底背离次数']
        self._crossOver             = True if param['金叉'] else False

    def onDaysLoad(self):
        return self._baseDate, -self.macdDays + 1

    def onInit(self, dataEngine, errorDataEngine):
        self._stockAllCodes = dataEngine.daysEngine.stockAllCodes

    def onStockDays(self, code, df):
        # 计算MACD
        diff, dea, bar = self._macd(df, self._macdIndicator)
        if diff is None: return

        # 计算极值
        extremas, peaks, bottoms = DyStockDataUtility.rwExtremas(df, w=self._extremaWindow, bottomIndicator=self._macdIndicator)

        # 不考虑MACD金叉时则考虑右边界
        if not self._crossOver:
            bottoms[df.index[-1]] = df.ix[-1, self._macdIndicator]

        if bottoms.size < self._bottomDeviationNbr: return

        # 极小值递减
        bottoms = bottoms[-self._bottomDeviationNbr:]
        if ((bottoms - bottoms.shift(1)) > 0).sum() > 0: return

        # 极小值对应的MACD的DIFF递增
        positions = [df.index.get_loc(index) for index in bottoms.index]
        
        # 确保diff的值不是NaN
        diff = diff[positions]
        if sum(np.isnan(diff)) > 0: return

        if ((diff[1:] - diff[:-1]) < 0).sum() > 0: return

        # 考虑金叉
        if self._crossOver:
            if not (diff[-1] > dea[-1] and diff[-2] < dea[-2]):
                return

        # 计算背离强度
        bottomsList = list(bottoms.values)
        bottomsChanges = list(map(lambda x,y:abs((x-y)/y), bottomsList[1:], bottomsList[:-1]))

        diffList = list(diff)
        diffChanges = list(map(lambda x,y:abs((x-y)/y), diffList[1:], diffList[:-1]))

        assert len(bottomsList) == len(diffList)

        deviationIntensity = list(map(lambda x,y:x*y, bottomsChanges, diffChanges))
        deviationIntensity = sum(deviationIntensity)*100
        
        # 设置结果
        pair = [code, self._stockAllCodes[code], deviationIntensity]
        self._result.append(pair)

    def _macd(self, df, indicator='close'):
        values = df[indicator]

        try:
            diff, dea, bar = talib.MACD(values.values, fastperiod=12, slowperiod=26, signalperiod=9)
            bar *= 2
        except Exception as ex:
            return None, None, None

        return diff, dea, bar

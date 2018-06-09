import math, operator

import pandas as pd
from pandas import Series, DataFrame
import talib

from ..DyStockSelectStrategyTemplate import *


class DySS_BBands(DyStockSelectStrategyTemplate):
    name = 'DySS_BBands'
    chName = '布林'

    colNames = ['代码', '名称', '标准差均值比(%)', '当日收盘价下轨线离差比', '当日最低价下轨线离差比']

    param = OrderedDict\
                ([
                    ('基准日期', datetime.today().strftime("%Y-%m-%d")),
                    ('向前N日周期', 10),
                    ('选几只股票', 50)
                ])

    def __init__(self, param, info):
        super().__init__(param, info)

        # unpack parameters
        self._baseDate              = param['基准日期']
        self._forwardNDays          = param['向前N日周期']
        self._selectStockNbr        = param['选几只股票']

    def onDaysLoad(self):
        return self._baseDate, -self._forwardNDays + 1

    def onInit(self, dataEngine, errorDataEngine):
        self._stockAllCodes = dataEngine.daysEngine.stockAllCodes
        
        self._startDay = dataEngine.daysEngine.tDaysOffset(self._baseDate, -self._forwardNDays + 1)
        self._endDay = dataEngine.daysEngine.tDaysOffset(self._baseDate, 0)

    def onStockDays(self, code, df):
        # 计算布林线
        upper, middle, lower = self._bbands(df)
        if middle is None: return

        # 计算标准差
        std = upper[-1] - middle[-1]
        if std == 0: return

        close = df.ix[self._endDay, 'close']
        low = df.ix[self._endDay, 'low']

        # 计算标准差均值比
        stdMeanRatio = std*100/middle[-1]
        if close < middle[-1]:
            stdMeanRatio *= -1

        # 计算比例
        closeRatio = (close - lower[-1])/std
        lowRatio = (low - lower[-1])/std

        # 设置结果
        pair = [code, self._stockAllCodes[code], stdMeanRatio, closeRatio, lowRatio]
        self._result.append(pair)
        self._result.sort(key=operator.itemgetter(2))

        self._result = self._result[:self._selectStockNbr]

    def _bbands(self, df):
        try:
            close = df['close']
        except Exception as ex:
            return None, None, None

        if close.shape[0] != self._forwardNDays:
            return None, None, None

        try:
            upper, middle, lower = talib.BBANDS(
                                close.values, 
                                timeperiod=self._forwardNDays,
                                # number of non-biased standard deviations from the mean
                                nbdevup=1,
                                nbdevdn=1,
                                # Moving average type: simple moving average here
                                matype=0)
        except Exception as ex:
            return None, None, None

        return upper, middle, lower

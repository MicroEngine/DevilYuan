from time import sleep
import pandas as pd
from collections import OrderedDict

try:
    from WindPy import *
except ImportError:
    pass

from DyCommon.DyCommon import *
from ...Common.DyStockCommon import *


class DyStockDataWind(object):
    """ Wind数据接口 """

    sectorCodeWindMap = {DyStockCommon.sz50Index: 'a00103010b000000',
                          DyStockCommon.hs300Index: 'a001030201000000',
                          DyStockCommon.zz500Index: 'a001030208000000'
                          }


    def __init__(self, info):
        self._info = info

        self._gateway = w

    def getDays(self, code, startDate, endDate, fields, name=None):
        """
            @return: df['datetime', indicators]
                     None - errors
                     [] - no data
        """
        if not fields:
            self._info.print('没有指定获取的指标', DyLogData.error)
            return None

        # 添加'volume'，由此判断停牌是否
        fields_ = ','.join(fields) if 'volume' in fields else ','.join(fields + ['volume'])

        for _ in range(3):
            windData = self._gateway.wsd(code, fields_, startDate, endDate)

            if windData.ErrorCode != 0:
                errorStr = "从Wind获取{0}:{1}, [{2}, {3}]WSD错误: {4}".format(code, name, startDate, endDate, windData.Data[0][0])
                if 'Timeout' in errorStr:
                    sleep(1)
                    continue
            break

        if windData.ErrorCode != 0:
            self._info.print(errorStr, DyLogData.error)
            return None

        try:
            df = pd.DataFrame(windData.Data,
                              index=[x.lower() for x in windData.Fields],
                              columns=windData.Times)

            df = df.T

            df = df.dropna(axis=1, how='all') # 去除全为NaN的列，比如指数数据，没有'mf_vol'
            df = df.ix[df['volume'] > 0, :] # 去除停牌的数据

            if 'volume' not in fields:
                del df['volume']

            df.reset_index(inplace=True) # 把时间索引转成列
            df.rename(columns={'index': 'datetime'}, inplace=True)

            # 把日期的HH:MM:SS转成 00:00:00
            df['datetime'] = df['datetime'].map(lambda x: x.strftime('%Y-%m-%d'))
            df['datetime'] = pd.to_datetime(df['datetime'], format='%Y-%m-%d')

            df = df[['datetime'] + fields]

        except:
            df = pd.DataFrame(columns=['datetime'] + fields)

        return df

    def _login(self):
        if not self._gateway.isconnected():
            self._info.print("登录Wind...")

            data = self._gateway.start()
            if data.ErrorCode != 0:
                self._info.print("登录Wind失败", DyLogData.error)
                return False

            self._info.print("登录Wind成功")

        return True

    def getTradeDays(self, startDate, endDate):
        if not self._login():
            return None

        self._info.print("开始从Wind获取交易日数据[{}, {}]...".format(startDate, endDate))

        data = w.tdayscount(startDate, endDate)
        if data.ErrorCode == 0:
            if data.Data[0][0] == 0:
                return [] # no trade days between startDate and endDate
            
            data = self._gateway.tdays(startDate, endDate)
            if data.ErrorCode == 0:
                return [x.strftime('%Y-%m-%d') for x in data.Data[0]]

        self._info.print("从Wind获取交易日数据失败[{0}, {1}]: {2}".format(startDate, endDate, data.Data[0][0]), DyLogData.error)
        return None

    def getStockCodes(self):
        if not self._login():
            return None

        self._info.print("开始从Wind获取股票代码表...")

        date = datetime.today()
        date = date.strftime("%Y%m%d")

        data = w.wset("SectorConstituent", "date={0};sectorId=a001010100000000".format(date))

        if data.ErrorCode != 0:
            self._info.print("从Wind获取股票代码表失败: {0}!".format(data.Data[0][0]), DyLogData.error)
            return None

        codes = {}
        for code, name in zip(data.Data[1], data.Data[2]):
            codes[code] = name

        return codes

    def getSectorStockCodes(self, sectorCode, startDate, endDate):
        if not self._login():
            return None

        self._info.print("开始从Wind获取[{0}]股票代码表[{1}, {2}]...".format(DyStockCommon.sectors[sectorCode], startDate, endDate))

        dates = DyTime.getDates(startDate, endDate)

        progress = DyProgress(self._info)
        progress.init(len(dates))

        codesDict = OrderedDict() # {date: {code: name}}
        for date_ in dates:
            date = date_.strftime("%Y%m%d")
            date_ = date_.strftime("%Y-%m-%d")

            data = w.wset("SectorConstituent", "date={0};sectorId={1}".format(date, self.sectorCodeWindMap[sectorCode]))

            if data.ErrorCode != 0:
                self._info.print("从Wind获取[{0}]股票代码表[{1}]失败: {2}!".format(DyStockCommon.sectors[sectorCode], date_, data.Data[0][0]), DyLogData.error)
                return None

            codes = {}
            if data.Data:
                for code, name in zip(data.Data[1], data.Data[2]):
                    codes[code] = name

            codesDict[date_] = codes

            progress.update()

        self._info.print("从Wind获取[{0}]股票代码表[{1}, {2}]完成".format(DyStockCommon.sectors[sectorCode], startDate, endDate))

        return codesDict


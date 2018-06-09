from time import sleep
import pandas as pd
import tushare as ts
import numpy as np

# copy from tushare
try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib3 import urlopen, Request
    pass

from pandas.compat import StringIO
from tushare.stock import cons as ct

from DyCommon.DyCommon import *
from EventEngine.DyEvent import *
from ..DyStockDataCommon import *
from .DyStockDataWind import *
from ...Common.DyStockCommon import *


class DyStockDataTicksGateway(object):
    """
        股票历史分笔数据网络接口
        分笔数据可以从新浪，腾讯，网易获取
        每个hand一个实例，这样可以防止数据互斥
    """


    def __init__(self, eventEngine, info, hand):
        self._eventEngine = eventEngine
        self._info = info
        self._hand = hand

        self._setTicksDataSource(DyStockDataCommon.defaultHistTicksDataSource)

        self._registerEvent()

    def _codeTo163Symbol(code):
        if code[0] in ['5', '6']:
            return '0' + code

        return '1' + code

    def _getTickDataFrom163(code=None, date=None, retry_count=3, pause=0.001):
        """
            从网易获取分笔数据
            网易的分笔数据只有最近5日的
            接口和返回的DF，保持跟tushare一致
        Parameters
        ------
            code:string
                        股票代码 e.g. 600848
            date:string
                        日期 format：YYYY-MM-DD
            retry_count : int, 默认 3
                        如遇网络等问题重复执行的次数
            pause : int, 默认 0
                        重复请求数据过程中暂停的秒数，防止请求间隔时间太短出现的问题
            return
            -------
            DataFrame 当日所有股票交易数据(DataFrame)
                    属性:成交时间、成交价格、价格变动，成交手、成交金额(元)，买卖类型
        """
        if code is None or len(code)!=6 or date is None:
            return None
        symbol = DyStockDataTicksGateway._codeTo163Symbol(code)
        yyyy, mm, dd = date.split('-')
        for _ in range(retry_count):
            sleep(pause)
            try:
                url = 'http://quotes.money.163.com/cjmx/{0}/{1}/{2}.xls'.format(yyyy, yyyy+mm+dd, symbol)
                socket = urlopen(url)
                xd = pd.ExcelFile(socket)
                df = xd.parse(xd.sheet_names[0], names=['time', 'price', 'change', 'volume', 'amount', 'type'])
                df['amount'] = df['amount'].astype('int64') # keep same as tushare
            except Exception as e:
                print(e)
                ex = e
            else:
                return df
        raise ex

    def _codeToTencentSymbol(code):
        if code[0] in ['5', '6']:
            return 'sh' + code

        return 'sz' + code

    def _getTickDataFromTencent(code=None, date=None, retry_count=3, pause=0.001):
        """
            从腾讯获取分笔数据
            接口和返回的DF，保持跟tushare一致
        Parameters
        ------
            code:string
                        股票代码 e.g. 600848
            date:string
                        日期 format：YYYY-MM-DD
            retry_count : int, 默认 3
                        如遇网络等问题重复执行的次数
            pause : int, 默认 0
                        重复请求数据过程中暂停的秒数，防止请求间隔时间太短出现的问题
            return
            -------
            DataFrame 当日所有股票交易数据(DataFrame)
                    属性:成交时间、成交价格、价格变动，成交手、成交金额(元)，买卖类型
        """
        if code is None or len(code)!=6 or date is None:
            return None
        symbol = DyStockDataTicksGateway._codeToTencentSymbol(code)
        yyyy, mm, dd = date.split('-')
        for _ in range(retry_count):
            sleep(pause)
            try:
                re = Request('http://stock.gtimg.cn/data/index.php?appn=detail&action=download&c={0}&d={1}'.format(symbol, yyyy+mm+dd))
                lines = urlopen(re, timeout=10).read()
                lines = lines.decode('GBK') 
                df = pd.read_table(StringIO(lines), names=['time', 'price', 'change', 'volume', 'amount', 'type'],
                                    skiprows=[0])      
            except Exception as e:
                print(e)
                ex = e
            else:
                return df
        raise ex

    def _codeToSinaSymbol(code):
        return DyStockDataTicksGateway._codeToTencentSymbol(code)

    def _getTickDataFromSina(code=None, date=None, retry_count=3, pause=0.001):
        """
            获取分笔数据
        Parameters
        ------
            code:string
                      股票代码 e.g. 600848
            date:string
                      日期 format：YYYY-MM-DD
            retry_count : int, 默认 3
                      如遇网络等问题重复执行的次数
            pause : int, 默认 0
                     重复请求数据过程中暂停的秒数，防止请求间隔时间太短出现的问题
         return
         -------
            DataFrame 当日所有股票交易数据(DataFrame)
                  属性:成交时间、成交价格、价格变动，成交手、成交金额(元)，买卖类型
        """
        if code is None or len(code)!=6 or date is None:
            return None
        symbol = DyStockDataTicksGateway._codeToSinaSymbol(code)
        for _ in range(retry_count):
            sleep(pause)
            try:
                re = Request('http://market.finance.sina.com.cn/downxls.php?date={}&symbol={}'.format(date, symbol))
                lines = urlopen(re, timeout=10).read()
                lines = lines.decode('GBK') 
                if len(lines) < 20:
                    return None
                df = pd.read_table(StringIO(lines), names=['time', 'price', 'change', 'volume', 'amount', 'type'],
                                   skiprows=[0])      
            except Exception as e:
                print(e)
                ex = e
            else:
                return df
        raise ex

    def _getTicks(self, code, date):
        """
            get history ticks data from network
            @returns: None - error happened, i.e. timer out or errors from server
                             If error happened, ticks engine will retry it.
                      DyStockHistTicksAckData.noData - no data for specified date
                      BSON format data - sucessful situation
        """
        switch = False

        for i, func in enumerate(self._ticksDataSource):
            # get ticks from data source
            data = self._getTicksByFunc(func, code, date)

            # 如果数据源应该有数据却没有数据或者发生错误，则换个数据源获取
            if data == DyStockHistTicksAckData.noData or data is None:
                # fatal error from data source
                if data is None:
                    self._ticksDataSourceErrorCount[i] += 1

                    if self._ticksDataSourceErrorCount[i] >= 3:
                        switch = True
                        self._ticksDataSourceErrorCount[i] = 0

            else: # 超时或者有数据, we don't think timer out as needed to switch data source, which might happen because of network
                break

        # Too many errors happend for data source, so we think it as fatal error and then switch data source
        if switch:
            oldTicksDataSourceName = self._ticksDataSourceName

            self._ticksDataSource = self._ticksDataSource[1:] + self._ticksDataSource[0:1]
            self._ticksDataSourceName = self._ticksDataSourceName[1:] + self._ticksDataSourceName[0:1]
            self._ticksDataSourceErrorCount = self._ticksDataSourceErrorCount[1:] + self._ticksDataSourceErrorCount[0:1]

            self._info.print('Hand {}: 历史分笔数据源切换{}->{}'.format(self._hand, oldTicksDataSourceName, self._ticksDataSourceName), DyLogData.warning)

        # convert return value to retain same interface for ticks engine
        return None if data == 'timer out' else data

    def _getTicksByFunc(self, func, code, date):
        """
            @return: [{indicator: value}], i.e. MongoDB BSON format
                     None - fatal error from server
                     DyStockHistTicksAckData.noData - no data for sepcified date
                     'timer out'
        """
        try:
            df = func(code[:-3], date=date)

            del df['change']

            df = df.dropna() # sometimes Sina will give wrong data that price is NaN
            df = df[df['volume'] > 0] # !!!drop 0 volume, added 2017/05/30, sometimes Sina contains tick with 0 volume.
            df = df.drop_duplicates(['time']) # drop duplicates

            # sometimes Sina will give wrong time format like some time for 002324.SZ at 2013-03-18 is '14.06'
            while True:
                try:
                    df['time']  =  pd.to_datetime(date + ' ' + df['time'], format='%Y-%m-%d %H:%M:%S')
                except ValueError as ex:
                    strEx = str(ex)
                    errorTime = strEx[strEx.find(date) + len(date) + 1:strEx.rfind("'")]
                    df = df[~(df['time'] == errorTime)]
                    continue
                break

            df.rename(columns={'time': 'datetime'}, inplace=True)

            df = df.T
            data = [] if df.empty else list(df.to_dict().values())

        except Exception as ex:
            if '当天没有数据' in str(ex):
                return DyStockHistTicksAckData.noData
            else:
                self._info.print("Hand {}: {}获取[{}, {}]Tick数据异常: {}".format(self._hand, func.__name__, code, date, str(ex)), DyLogData.error)
                if 'timed out' in str(ex):
                    return 'timer out'
                else:
                    return None

        return data if data else DyStockHistTicksAckData.noData

    def _stockHistTicksReqHandler(self, event):
        code = event.data.code
        date = event.data.date

        data = self._getTicks(code, date)

        # put ack event
        event = DyEvent(DyEventType.stockHistTicksAck)
        event.data = DyStockHistTicksAckData(code, date, data)

        self._eventEngine.put(event)

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockHistTicksReq + str(self._hand), self._stockHistTicksReqHandler, self._hand)
        self._eventEngine.register(DyEventType.updateHistTicksDataSource, self._updateHistTicksDataSourceHandler, self._hand)

    def _updateHistTicksDataSourceHandler(self, event):
        self._setTicksDataSource(event.data)

    def _setTicksDataSource(self, dataSource):
        if dataSource == '新浪':
            self._ticksDataSource = [self.__class__._getTickDataFromSina]
            self._ticksDataSourceName = ['新浪']
        elif dataSource == '腾讯':
            self._ticksDataSource = [self.__class__._getTickDataFromTencent]
            self._ticksDataSourceName = ['腾讯']
        else: # '智能'
            self._ticksDataSource = [self.__class__._getTickDataFromTencent, self.__class__._getTickDataFromSina]
            self._ticksDataSourceName = ['腾讯', '新浪']
            
        self._ticksDataSourceErrorCount = [0]*len(self._ticksDataSource)


class DyStockDataGateway(object):
    """
        股票数据网络接口
        日线数据从Wind获取，分笔数据可以从新浪，腾讯，网易获取
    """


    def __init__(self, eventEngine, info, registerEvent=True):
        self._eventEngine = eventEngine
        self._info = info

        if DyStockCommon.WindPyInstalled:
            self._wind = DyStockDataWind(self._info)

        if registerEvent:
            self._registerEvent()

    def _registerEvent(self):
        """
            register events for each ticks gateway for each hand
        """
        # new DyStockDataTicksGateway instance for each ticks hand to avoid mutex
        self._ticksGateways = [DyStockDataTicksGateway(self._eventEngine, self._info, i) for i in range(DyStockDataEventHandType.stockHistTicksHandNbr)]

    def _getTradeDaysFromTuShare(self, startDate, endDate):
        try:
            df = ts.trade_cal()

            df = df.set_index('calendarDate')
            df = df[startDate:endDate]
            dfDict = df.to_dict()

            # get trade days
            dates = DyTime.getDates(startDate, endDate, strFormat=True)
            tDays = []
            for date in dates:
                if dfDict['isOpen'][date] == 1:
                    tDays.append(date)

            return tDays

        except Exception as ex:
            self._info.print("从TuShare获取[{}, {}]交易日数据异常: {}".format(startDate, endDate, str(ex)), DyLogData.error)
            
        return None

    def getTradeDays(self, startDate, endDate):
        """
            Wind可能出现数据错误，所以需要从其他数据源做验证
        """
        # from Wind
        if 'Wind' in DyStockCommon.defaultHistDaysDataSource:
            windTradeDays = self._wind.getTradeDays(startDate, endDate)
            tradeDays = windTradeDays

        # always get from TuShare
        tuShareTradeDays = self._getTradeDaysFromTuShare(startDate, endDate)
        tradeDays = tuShareTradeDays

        # verify
        if 'Wind' in DyStockCommon.defaultHistDaysDataSource:
            if windTradeDays is None or tuShareTradeDays is None or len(windTradeDays) != len(tuShareTradeDays):
                self._info.print("Wind交易日数据{}跟TuShare{}不一致".format(windTradeDays, tuShareTradeDays), DyLogData.error)
                return None

            for x, y in zip(windTradeDays, tuShareTradeDays):
                if x != y:
                    self._info.print("Wind交易日数据{}跟TuShare{}不一致".format(windTradeDays, tuShareTradeDays), DyLogData.error)
                    return None

        return tradeDays

    def getStockCodes(self):
        """
            获取股票代码表
        """
        # from Wind
        if 'Wind' in DyStockCommon.defaultHistDaysDataSource:
            windCodes = self._wind.getStockCodes()
            codes = windCodes

        # from TuShare
        if 'TuShare' in DyStockCommon.defaultHistDaysDataSource:
            tuShareCodes = self._getStockCodesFromTuShare()
            codes = tuShareCodes

        # verify
        if 'Wind' in DyStockCommon.defaultHistDaysDataSource and 'TuShare' in DyStockCommon.defaultHistDaysDataSource:
            if windCodes is None or tuShareCodes is None or len(windCodes) != len(tuShareCodes):
                self._info.print("Wind股票代码表跟TuShare不一致", DyLogData.error)
                return None

            for code, name in windCodes.items():
                name_ = tuShareCodes.get(code)
                if name_ is None or name_ != name:
                    self._info.print("Wind股票代码表跟TuShare不一致", DyLogData.error)
                    return None

        return codes

    def getSectorStockCodes(self, sectorCode, startDate, endDate):
        return self._wind.getSectorStockCodes(sectorCode, startDate, endDate)

    def getDays(self, code, startDate, endDate, fields, name=None):
        """
            获取股票日线数据
            @return: MongoDB BSON format like [{'datetime': value, 'indicator': value}]
                     None - erros
        """
        # get from Wind
        if 'Wind' in DyStockCommon.defaultHistDaysDataSource:
            windDf = self._wind.getDays(code, startDate, endDate, fields, name)
            df = windDf

        # get from TuShare
        if 'TuShare' in DyStockCommon.defaultHistDaysDataSource:
            tuShareDf = self._getDaysFromTuShare(code, startDate, endDate, fields, name)
            df = tuShareDf

        # verify data
        if 'Wind' in DyStockCommon.defaultHistDaysDataSource and 'TuShare' in DyStockCommon.defaultHistDaysDataSource:
            if windDf is None or tuShareDf is None or windDf.shape[0] != tuShareDf.shape[0]:
                self._info.print("{}({})日线数据[{}, {}]: Wind和TuShare不相同".format(code, name, startDate, endDate), DyLogData.error)
                return None

            # remove adjfactor because Sina adjfactor is different with Wind
            fields_ = [x for x in fields if x != 'adjfactor']
            fields_ = ['datetime'] + fields_

            if (windDf[fields_].values != tuShareDf[fields_].values).sum() > 0:
                self._info.print("{}({})日线数据[{}, {}]: Wind和TuShare不相同".format(code, name, startDate, endDate), DyLogData.error)
                return None

        # BSON
        return None if df is None else list(df.T.to_dict().values())

    def isNowAfterTradingTime(self):
        today = datetime.now().strftime("%Y-%m-%d")

        for _ in range(3):
            days = self.getTradeDays(today, today)
            if days is not None:
                break

            sleep(1)
        else:
            self._info.print("@DyStockDataGateway.isNowAfterTradingTime: 获取交易日数据[{}, {}]失败3次".format(today, today), DyLogData.error)
            return None # error

        if today in days:
            year, month, day = today.split('-')
            afterTradeTime = datetime(int(year), int(month), int(day), 18, 0, 0)

            if datetime.now() < afterTradeTime:
                return False

        return True

    def _getDaysFromTuShareOld(self, code, startDate, endDate, fields, name=None, verify=False):
        """
            从tushare获取股票日线数据。
            保持跟Wind接口一致，由于没法从网上获取净流入量和金额，所以这两个字段没有。
            策略角度看，其实这两个字段也没什么用。
            @verify: True - 不同网上的相同字段会相互做验证。
            @return: df['datetime', indicators]
                     None - errors
                     [] - no data
        """
        code = code[:-3]

        try:
            # 从凤凰网获取换手率，成交量是手（没有整数化过，比如2004.67手）
            ifengDf = ts.get_hist_data(code, startDate, endDate).sort_index()

            # 以无复权方式从腾讯获取OHCLV，成交量是手（整数化过）
            if verify:
                tcentDf = ts.get_k_data(code, startDate, endDate, autype=None).sort_index()

            # 从新浪获取复权因子，成交量是股。新浪的数据是后复权的，无复权方式是tushare根据复权因子实现的。
            sinaDf = ts.get_h_data(code, startDate, endDate, autype=None, drop_factor=False)
            if sinaDf is None: # If no data, TuShare return None
                sinaDf = pd.DataFrame(columns=['open', 'high', 'close', 'low', 'volume', 'amount', 'factor'])
            else:
                sinaDf = sinaDf.sort_index()
        except Exception as ex:
            self._info.print("从TuShare获取{}({})日线数据[{}, {}]失败: {}".format(code, name, startDate, endDate, ex), DyLogData.error)
            return None

        # 数据相互验证
        if verify:
            # OHLC
            for indicator in ['open', 'high', 'close', 'low']:
                if len(tcentDf[indicator].values) != len(sinaDf[indicator].values):
                    self._info.print("{}({})日线数据OHLC[{}, {}]: 腾讯和新浪不相同".format(code, name, startDate, endDate), DyLogData.error)
                    return None

                if (tcentDf[indicator].values != sinaDf[indicator].values).sum() > 0:
                    self._info.print("{}({})日线数据OHLC[{}, {}]: 腾讯和新浪不相同".format(code, name, startDate, endDate), DyLogData.error)
                    return None

            # volume
            if len(ifengDf['volume'].values) != len(sinaDf['volume'].values):
                self._info.print("{}({})日线数据Volume[{}, {}]: 凤凰网和新浪不相同".format(code, name, startDate, endDate), DyLogData.error)
                return None

            if (np.round(ifengDf['volume'].values*100) != np.round(sinaDf['volume'].values)).sum() > 0:
                self._info.print("{}({})日线数据Volume[{}, {}]: 凤凰网和新浪不相同".format(code, name, startDate, endDate), DyLogData.error)
                return None

        # construct new DF
        df = pd.concat([sinaDf[['open', 'high', 'close', 'low', 'volume', 'amount', 'factor']], ifengDf['turnover']], axis=1)
        df.index.name = None

        # change to Wind's indicators
        df.reset_index(inplace=True) # 把时间索引转成列
        df.rename(columns={'index': 'datetime', 'amount': 'amt', 'turnover': 'turn', 'factor': 'adjfactor'}, inplace=True)

        # 把日期的HH:MM:SS转成 00:00:00
        df['datetime'] = df['datetime'].map(lambda x: x.strftime('%Y-%m-%d'))
        df['datetime'] = pd.to_datetime(df['datetime'], format='%Y-%m-%d')

        # select according @fields
        df = df[['datetime'] + fields]

        return df

    def _getStockCodesFromTuShare(self):
        try:
            df = ts.get_today_all() # it's slow because TuShare will get one page by one page
        except Exception as ex:
            return None

        if df is None or df.empty:
            return None

        codes = {}
        data = df[['code', 'name']].values.tolist()
        for code, name in data:
            if code[0] == '6':
                codes[code + '.SH'] = name
            else:
                codes[code + '.SZ'] = name

        return codes

    def _getDaysFrom163(self, code, startDate, endDate, retry_count=3, pause=0.001):
        """
            从网易获取个股日线数据，指数和基金（ETF）除外
            @code: DevilYuan Code

        """
        symbol = ('0' + code[:6]) if code[-2:] == 'SH' else ('1' + code[:6])

        for _ in range(retry_count):
            sleep(pause)
            try:
                url = 'http://quotes.money.163.com/service/chddata.html?code={}&start={}&end={}&fields=TCLOSE;HIGH;LOW;TOPEN;TURNOVER;VOTURNOVER;VATURNOVER'
                url = url.format(symbol, startDate.replace('-', ''), endDate.replace('-', ''))
                re = Request(url)
                lines = urlopen(re, timeout=10).read()
                lines = lines.decode('GBK') 
                df = pd.read_table(StringIO(lines),
                                   sep=',',
                                   names=['date', 'code', 'name', 'close', 'high', 'low', 'open', 'turnover', 'volume', 'amount'],
                                   skiprows=[0])
            except Exception as e:
                print(e)
                ex = e
            else:
                df = df[['date', 'open', 'high', 'close', 'low', 'volume', 'amount', 'turnover']] # return columns
                df = df.set_index('date')
                df = df.sort_index(ascending=False)
                return df
        raise ex

    def _getCodeDaysFromTuShare(self, code, startDate, endDate, fields, name=None):
        """
            从TuShare获取个股日线数据
        """
        tuShareCode = code[:-3]

        try:
            # 从网易获取换手率
            netEasyDf = self._getDaysFrom163(code, startDate, endDate).sort_index()

            # 从新浪获取复权因子，成交量是股。新浪的数据是后复权的，无复权方式是tushare根据复权因子实现的。
            sinaDf = ts.get_h_data(tuShareCode, startDate, endDate, autype=None, drop_factor=False)
            if sinaDf is None: # If no data, TuShare return None
                sinaDf = pd.DataFrame(columns=['open', 'high', 'close', 'low', 'volume', 'amount', 'factor'])
            else:
                sinaDf = sinaDf.sort_index()
        except Exception as ex:
            self._info.print("从TuShare获取{}({})日线数据[{}, {}]失败: {}".format(code, name, startDate, endDate, ex), DyLogData.error)
            return None

        # construct new DF
        df = pd.concat([sinaDf[['open', 'high', 'close', 'low', 'volume', 'amount', 'factor']], netEasyDf['turnover']], axis=1)
        df.index.name = None

        # change to Wind's indicators
        df.reset_index(inplace=True) # 把时间索引转成列
        df.rename(columns={'index': 'datetime', 'amount': 'amt', 'turnover': 'turn', 'factor': 'adjfactor'}, inplace=True)

        # 把日期的HH:MM:SS转成 00:00:00
        df['datetime'] = df['datetime'].map(lambda x: x.strftime('%Y-%m-%d'))
        df['datetime'] = pd.to_datetime(df['datetime'], format='%Y-%m-%d')

        # select according @fields
        df = df[['datetime'] + fields]

        return df

    def _getIndexDaysFromTuShare(self, code, startDate, endDate, fields, name=None):
        """
            从TuShare获取指数日线数据
        """
        tuShareCode = code[:-3]

        try:
            df = ts.get_h_data(tuShareCode, startDate, endDate)
            if df is None: # If no data, TuShare return None
                df = pd.DataFrame(columns=['open', 'high', 'close', 'low', 'volume', 'amount'])
            else:
                df = df.sort_index()
        except Exception as ex:
            self._info.print("从TuShare获取{}({})日线数据[{}, {}]失败: {}".format(code, name, startDate, endDate, ex), DyLogData.error)
            return None

        # no turn and factor for index
        df['turnover'] = 0
        df['factor'] = 1
        df.index.name = None

        # change to Wind's indicators
        df.reset_index(inplace=True) # 把时间索引转成列
        df.rename(columns={'index': 'datetime', 'amount': 'amt', 'turnover': 'turn', 'factor': 'adjfactor'}, inplace=True)

        # 把日期的HH:MM:SS转成 00:00:00
        df['datetime'] = df['datetime'].map(lambda x: x.strftime('%Y-%m-%d'))
        df['datetime'] = pd.to_datetime(df['datetime'], format='%Y-%m-%d')

        # select according @fields
        df = df[['datetime'] + fields]

        return df

    def _getFundDaysFromTuShare(self, code, startDate, endDate, fields, name=None):
        """
            从tushare获取基金（ETF）日线数据。
        """
        tuShareCode = code[:-3]

        try:
            # 从凤凰网获取换手率，成交量是手（没有整数化过，比如2004.67手）
            df = ts.get_hist_data(tuShareCode, startDate, endDate).sort_index()

            # 以无复权方式从腾讯获取OHCLV，成交量是手（整数化过）
            # 此接口支持ETF日线数据
            #tcentDf = ts.get_k_data(code, startDate, endDate, autype=None).sort_index()
        except Exception as ex:
            self._info.print("从TuShare获取{}({})日线数据[{}, {}]失败: {}".format(code, name, startDate, endDate, ex), DyLogData.error)
            return None

        df['volume'] = df['volume']*100

        # !!!TuShare没有提供换手率和复权因子，所以只能假设。
        # 策略针对ETF的，需要注意。
        df['turnover'] = 0
        df['factor'] = 1
        df.index.name = None

        # change to Wind's indicators
        df.reset_index(inplace=True) # 把时间索引转成列
        df.rename(columns={'index': 'datetime', 'amount': 'amt', 'turnover': 'turn', 'factor': 'adjfactor'}, inplace=True)

        # 把日期的HH:MM:SS转成 00:00:00
        df['datetime'] = df['datetime'].map(lambda x: x.strftime('%Y-%m-%d'))
        df['datetime'] = pd.to_datetime(df['datetime'], format='%Y-%m-%d')

        # select according @fields
        df = df[['datetime'] + fields]

        return df

    def _getDaysFromTuShare(self, code, startDate, endDate, fields, name=None):
        """
            从tushare获取股票日线数据（含指数和基金（ETF））。
            !!!TuShare没有提供换手率和复权因子，所以只能假设。
            策略针对ETF的，需要注意。
            保持跟Wind接口一致，由于没法从网上获取净流入量和金额，所以这两个字段没有。
            策略角度看，其实这两个字段也没什么用。
            @verify: True - 不同网上的相同字段会相互做验证。
            @return: df['datetime', indicators]
                     None - errors
                     [] - no data
        """
        if code in DyStockCommon.indexes:
            return self._getIndexDaysFromTuShare(code, startDate, endDate, fields, name)
        
        if code in DyStockCommon.funds:
            return self._getFundDaysFromTuShare(code, startDate, endDate, fields, name)

        return self._getCodeDaysFromTuShare(code, startDate, endDate, fields, name)
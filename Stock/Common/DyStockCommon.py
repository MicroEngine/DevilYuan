from datetime import datetime
from collections import OrderedDict


class DyStockCommon(object):
    indexes = OrderedDict([
                        ('000001.SH', '上证指数'),
                        ('399001.SZ', '深证成指'),
                        ('399006.SZ', '创业板指'),
                        ('399005.SZ', '中小板指'),
                        ])

    funds = {'510050.SH': '50ETF',
             '510300.SH': '300ETF',
             '510500.SH': '500ETF'
             }

    sectors = {'000016.SH': '上证50',
               '399300.SZ': '沪深300',
               '399905.SZ': '中证500'
               }

    # 板块指数
    sz50Index = '000050.SH'
    hs300Index = '399300.SZ'
    zz500Index = '399905.SZ'

    # 大盘指数
    shIndex = '000001.SH'
    szIndex = '399001.SZ'
    cybIndex = '399006.SZ'
    zxbIndex = '399005.SZ'

    #!!! 综指是全市场所有的股票，上面四个则不是。
    # 创小板，同花顺做了调整，统一是用的所对应板的全市场的股票成交额。
    cybzIndex = '399102.SZ' # 创业板综
    zxbzIndex = '399101.SZ' # 中小板综

    etf50 = '510050.SH' # 50ETF是2005.02.23上市的
    etf300 = '510300.SH' # 300ETF是2012.05.28上市的
    etf500 = '510500.SH' # 500ETF是2013.03.15上市的

    dayKChartPeriodNbr = 90 # 日K线前后交易日周期
    rollingWindowW = 4 # 滑动窗口(w), 绘制技术分析图表时使用
    hsarMode = '极值平均' # HSAR模式, 绘制技术分析图表时使用
    trendLinePeriods = [30, 60]

    indicatorNameTable = {'open':'开盘价', 'high':'最高价', 'low':'最低价', 'close':'收盘价', 'volume':'成交量'}

    limitUpPct = 9.946 # 涨停时的涨幅(%), >=
    limitDownPct = -9.946 # 跌停时的涨幅(%), <=

    # Devil启动时从配置文件读入，这个配置在Stock模块里共享。默认是Wind
    defaultHistDaysDataSource = ['Wind'] # Wind and TuShare，如果数据源是两个或者以上，则数据相互做验证。单个则不做验证。这里包括验证交易日数据，股票代码表和日线数据。
    WindPyInstalled = True    

    # 同花顺个股资料（F10）link
    jqkaStockF10Link = 'http://basic.10jqka.com.cn/{}/'

    # 仿浏览器的HTTP、HTTPS的请求头部
    requestHeaders = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}


    def getIndexByName(indexName):
        for code, name in DyStockCommon.indexes.items():
            if name == indexName:
                return code

        return None

    def getIndexSectorByName(indexName):
        for code, name in DyStockCommon.indexes.items():
            if name == indexName:
                return code

        for code, name in DyStockCommon.sectors.items():
            if name == indexName:
                return code 

        return None

    def getIndexesSectors():
        return dict(DyStockCommon.indexes, **DyStockCommon.sectors)

    def getIndex(code):
        """
            获取个股对应的大盘指数
        """
        if code[-2:] == 'SH': return DyStockCommon.shIndex

        if code[:3] == '002': return DyStockCommon.zxbIndex
        if code[:3] == '300': return DyStockCommon.cybIndex
            
        if code[-2:] == 'SZ': return DyStockCommon.szIndex

        assert(0)
        return None

    def getEtf(code):
        """
            获取个股对应的ETF代码
        """
        if code[-2:] == 'SH': return DyStockCommon.etf300

        if code[:3] == '002': return DyStockCommon.etf500
        if code[:3] == '300': return DyStockCommon.etf500
            
        if code[-2:] == 'SZ': return DyStockCommon.etf500

        assert(0)
        return None

    def getDyStockCode(code):
        return (code[:6] + '.SH') if code[0] in ['6', '5'] else (code[:6] + '.SZ')

    def getDyStockCodes(codes):
        if not isinstance(codes, list): return None

        return [DyStockCommon.getDyStockCode(code) for code in codes]

    def getRelativeTime(stockTime):
        morningStart = datetime(stockTime.year, stockTime.month, stockTime.day, 9, 30, 0)
        afternoonStart = datetime(stockTime.year, stockTime.month, stockTime.day, 13, 0, 0)

        relativeSeconds = 0

        if stockTime < morningStart:
            relativeSeconds = 0
        elif morningStart <= stockTime < afternoonStart:
            relativeSeconds = min((stockTime - morningStart).total_seconds(), 2*60*60)
        else:
            relativeSeconds = min((stockTime - afternoonStart).total_seconds(), 2*60*60) + 2*60*60

        return int(relativeSeconds)

    def getRelativeTimeByTime(time):
        h, m, s = time.split(':')
        h, m, s = int(h), int(m), int(s)

        if h < 13:
            return (h - 9)*60*60 + m*60 + s - 30*60

        return (h - 13)*60*60 + m*60 + s

    def getTimeInterval(time1, time2):
        """
            获取时间差，单位是秒
            @time: 'hh:mm:ss'
        """
        time1S = int(time1[:2])*3600 + int(time1[3:5])*60 + int(time1[-2:])
        time2S = int(time2[:2])*3600 + int(time2[3:5])*60 + int(time2[-2:])

        # 横跨上下午
        if int(time1[:2]) == 11 and int(time2[:2]) == 13:
            deltaMorning = 11*3600 + 30*60 - time1S
            deltaAfternoon = time2S - 13*3600

            return max(deltaMorning, 0) + max(deltaAfternoon, 0)

        return time2S - time1S

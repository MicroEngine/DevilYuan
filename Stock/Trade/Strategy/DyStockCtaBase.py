from datetime import datetime


class DyStockCtaBarData(object):
    """ K线数据 """

    slippage = 0 # 单位是成交价的千分之


    def __init__(self, mode):
        """
            @mode: Bar的格式，like '1d', '1m', '5m', '30m' and etc.
                   回测时需要基于此值撮合成交
        """
        self.mode = mode

        self.code = None            # 代码
        self.name = None            # 名称
    
        self.open = None            # Bar的OHLC
        self.high = None
        self.low = None
        self.close = None

        # 添加这些主要为了Bar回测时方便，这样策略可以同时适用tick和bar回测。
        self.curOpen = None         # 当日开盘价
        self.curLow = None          # 当日最新最低价
        self.curHigh = None         # 当日最新最高价

        self.preClose = None        # 前一日收盘价，不会生成开盘当日的Bar
        
        self.date = None            # bar结束的时间，日期
        self.time = None            # 时间
        self.datetime = None        # python的datetime时间对象
        
        self.volume = None          # 成交量

        # 最新五档行情，也就是Bar的最后一个Tick的五档行情。
        # 只有实盘时才有，回测数据没有五档行情。
        self.bidPrices = None # list bid1->bid5, 0 -> 4
        
        self.askPrices = None # list

    def __getattr__(self, name):
        """
            获取股票价格
            涨停时，没有卖盘（ask）
            跌停时，没有买盘（bid）
        """
        if name == 'price':
            return self.close

        elif name[:-1] == 'bidPrice': # 卖出
            if self.bidPrices is None: # 回测
                return self.close - self.close*self.slippage/1000

            elif self.bidPrices[int(name[-1]) - 1] == 0: # 跌停
                return self.close

            else:
                return self.bidPrices[int(name[-1]) - 1]

        elif name[:-1] == 'askPrice': # 买入
            if self.askPrices is None:
                return self.close + self.close*self.slippage/1000

            elif self.askPrices[int(name[-1]) - 1] == 0: # 涨停
                return self.close

            else:
                return self.askPrices[int(name[-1]) - 1]

        elif name == 'amount': # !!!Bar的成交额没有考虑
            return 0

        raise AttributeError


class DyStockCtaTickData(object):
    """ Tick数据 """

    slippage = 0 # 单位是成交价的千分之


    def __init__(self, sinaCode=None, sinaTick=None):
        if sinaCode is None:
            self._defaultInit()
        else:
            self.convertFromSina(sinaCode, sinaTick)

    def _defaultInit(self):
        self.code = None
        self.name = None

        # tick的时间
        self.date = None            # 日期，string
        self.time = None            # 时间，string
        self.datetime = None        # python的datetime时间对象

        # OHLC
        self.open = None            # 当日开盘价
        self.high = None            # 最新最高价
        self.low = None             # 最新最低价
        self.preClose = None        # 前日收盘价

        # 成交数据
        self.price = None           # 最新成交价
        self.volume = None          # 最新成交量
        self.amount = None          # 最新成交额，单位是元
        
        # 五档行情, 回测数据没有五档行情
        self.bidPrices = None # list bid1->bid5, 0 -> 4
        self.bidVolumes = None # list
        
        self.askPrices = None # list
        self.askVolumes = None # list

    def __getattr__(self, name):
        """
            获取股票价格
            涨停时，没有卖盘（ask）
            跌停时，没有买盘（bid）
        """
        # 添加此属性，主要为了跟Bar属性保持一致
        if name == 'curOpen': 
            return self.open

        if name == 'curHigh':
            return self.high

        if name == 'curLow':
            return self.low

        if name[:-1] == 'bidPrice': # 卖出
            if self.bidPrices is None: # 回测
                return self.price - self.price*self.slippage/1000

            elif self.bidPrices[int(name[-1]) - 1] == 0: # 跌停
                return self.price

            else:
                return self.bidPrices[int(name[-1]) - 1]

        elif name[:-1] == 'askPrice': # 买入
            if self.askPrices is None:
                return self.price + self.price*self.slippage/1000

            elif self.askPrices[int(name[-1]) - 1] == 0: # 涨停
                return self.price

            else:
                return self.askPrices[int(name[-1]) - 1]

        raise AttributeError

    def convertFromSina(self, sinaCode, sinaTick):
        self.code = sinaCode[2:] + '.' + sinaCode[:2].upper()
        self.name = sinaTick['name']

        self.date = sinaTick['date']
        self.time = sinaTick['time']
        self.datetime = datetime.strptime(self.date + ' ' + self.time,'%Y-%m-%d %H:%M:%S')

        self.open = sinaTick['open']
        self.high = sinaTick['high']
        self.low = sinaTick['low']
        self.preClose = sinaTick['pre_close']

        self.price = sinaTick['now']
        self.volume = sinaTick['volume']
        self.amount = sinaTick['amount']

        self.bidPrices = [sinaTick['bid1'], sinaTick['bid2'], sinaTick['bid3'], sinaTick['bid4'], sinaTick['bid5']]
        self.bidVolumes = [sinaTick['bid1_volume'], sinaTick['bid2_volume'], sinaTick['bid3_volume'], sinaTick['bid4_volume'], sinaTick['bid5_volume']]

        self.askPrices = [sinaTick['ask1'], sinaTick['ask2'], sinaTick['ask3'], sinaTick['ask4'], sinaTick['ask5']]
        self.askVolumes = [sinaTick['ask1_volume'], sinaTick['ask2_volume'], sinaTick['ask3_volume'], sinaTick['ask4_volume'], sinaTick['ask5_volume']]


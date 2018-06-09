from ..Common.DyStockCommon import *


class DyStockTradeEventHandType:
    stockCtaEngine = 0
    stockSinaQuotation = 1
    brokerEngine = 2
    #qqMsgEngine = 3
    wxEngine = 3
    #rpcEngine = 4

    other = 4
    nbr = 5


class DyStockTradeCommon:
    enableTimerLog = False # 打开Timer日志，主要是调试新浪的Tick数据
    enableSinaTickOptimization = True # 打开新浪Tick数据的优化，主要是调试新浪的Tick数据
    enableCtaEngineTickOptimization = True # 打开实盘CTA引擎的Tick数据的优化，主要是调试实盘策略
    T1 = True # T+1模式，False为T+0模式，主要为了实盘调试
    testRpc = False # 测试RPC

    strategyPreparedDataDay = None # 策略准备数据的日期, 通过UI设置


    #------------------------ 实盘相关 ------------------------
    # 实盘时，停损模块使用的买入和卖出价，为了容易成交
    #!!! 按逻辑，这个应该放到CTA Enginge，但考虑到停损模块的独立运行，则提到这里。基于现在的架构，回测时启动停损模块有效。
    #!!! 停损模块，建议实盘时不要使用，而由策略自己实现。
    buyPrice = 'askPrice1' # 买入使用价，即五档的卖盘
    sellPrice = 'bidPrice1' # 卖出使用价，即五档的买盘

    # 如果剩余资金不足总资产的@allPosPreliminaryRatio%，则满仓。
    # 同样，为了防止小单买入，如果买入资金不足@allPosPreliminaryRatio%，则不买入。
    #!!! 这个参数是很重要的仓控参数，决定着仓位分配的粒度。资金的大小，这个参数也不一样。
    allPosPreliminaryRatio = 8

    brokerageCommissionRatio = 0.0003 # 券商交易佣金比例


    accountMap = {'gtja': '国泰居安',
                  'yh': '银河证券',
                  'fz': '方正证券',
                  'simu1': '模拟1',
                  'simu2': '模拟2',
                  'simu3': '模拟3',
                  'simu4': '模拟4',
                  'simu5': '模拟5',
                  'simu6': '模拟6',
                  'simu7': '模拟7',
                  'simu8': '模拟8',
                  'simu9': '模拟9',
                  }

    def getTradeCost(code, type, price, volume):
        """
            获取每笔交易的交易成本

            股票交易手续费包括三部分：
                1.印花税：成交金额的1‰,只有卖出时收取。
                2.过户费(仅上海股票收取)：每1000股收取1元，不足1000股按1元收取。
                3.券商交易佣金：最高为成交金额的3‰，最低5元起，单笔交易佣金不满5元按5元收取
        """
        stampTax = price*volume*0.001 if type == DyStockOpType.sell else 0

        transferFee = (volume + 999)//1000 if code[0] in ['6', '5'] else 0

        # 指数基金没有印花税和过户费
        if code in DyStockCommon.funds:
            stampTax = 0
            transferFee = 0

        brokerageCommission = max(5, price*volume*DyStockTradeCommon.brokerageCommissionRatio)

        return stampTax + transferFee + brokerageCommission

    def getBuyVol(cash, code, price):
        volume = ((cash/price)//100)*100

        while volume > 0:
            tradeCost = DyStockTradeCommon.getTradeCost(code, DyStockOpType.buy, price, volume)
            if tradeCost + price*volume <= cash:
                break

            volume -= 100

        return volume

    def getSellVol(cash, code, price):
        """
            获取需要卖的数量
            @cash: 卖出后的现金
        """
        volume = ((cash/price + 99)//100)*100

        while True:
            tradeCost = DyStockTradeCommon.getTradeCost(code, DyStockOpType.sell, price, volume)
            if price*volume - tradeCost >= cash:
                break

            volume += 100

        return volume


class DyStockOpType:
    buy = '买入'
    sell = '卖出'


class DyStockSellReason:
    stopLoss = '止损'
    stopLossStep = '阶梯止损'
    stopProfit = '止盈'
    stopTime = '止时'
    liquidate = '清仓'
    strategy = '策略' # 策略主动卖出
    manualSell = '手工卖出'


class DyStockDeal:
    """
        股票成交单
        DevilYuan系统里成交单的type只有'买入'和'卖出'。
        这个跟券商系统有区别，券商会有'撤单成交'类型。
    """

    def __init__(self, datetime, type, code, name, price, volume, tradeCost=None, sellReason=None, signalInfo=None, entrustDatetime=None):
        """
            @singalInfo: 成交信号信息（也即是说进场和出场的信号信息），一般是策略使用，主要是为了调试回测结果
            @entrustDatetime: datetime, 这笔成交对应的委托时间，现在是回测时使用
        """
        self.entrustDatetime = entrustDatetime # 委托时间
        self.datetime = datetime # 成交时间，实盘时则从券商获取，类型未必是datetime

        self.type = type

        self.code = code
        self.name = name

        self.price = price # 成交价格
        self.volume = volume # 成交数量

        self.strategyCls = None

        #------------- Only for live trading -------------
        self.dyDealId = None # DevilYuan系统中的唯一成交编号，通常是broker.成交编号。成交编号为日期+计数，主要是考虑连续多日实盘的唯一性。
        self.brokerDealId = None # 券商的成交编号

        #------------- Only for Backtesting -------------
        self.tradeCost = tradeCost # 交易成本

        # for sell
        self.pnl = None
        self.pnlRatio = None
        self.holdingPeriod = None
        self.xrd = None # 持有期内是否发生除权除息
        self.minPnlRatio = None # 持有周期内的最大亏损比

        self.sellReason = sellReason
        self.signalInfo = signalInfo


class DyStockEntrust:
    """
        股票委托单，只为实盘

        证券端委托状态：（来自恒生HOMS）, 参考用
        entrust_status    委托状态
        0    未报
        1    待报
        2    已报
        3    已报待撤
        4    部成待撤
        5    部撤         # “部撤”指的是部分股票撤单，部分撤单，是指部分股数成交，另外部分没有成交。
        6    已撤
        7    部成
        8    已成
        9    废单
        A    待确认
    """

    class Status:
        """
            简化和归类委托状态
        """
        notDealed = '未成' # 其它状态
        partDealed = '部成'
        allDealed = '已成'
        cancelled = '已撤' # 部撤，已撤
        discarded = '废单'


    def __init__(self, datetime, type, code, name, price, volume):
        self.entrustDatetime = datetime # 委托时间, Tick或者Bar的时间，不是本地时间

        self.type = type

        self.code = code
        self.name = name

        self.price = price # 委托价格
        self.totalVolume = volume # 委托数量(股)
        self.dealedVolume = 0 # 成交数量(股)

        self.matchedDealedVolume = 0 # 多少成交数量跟成交单匹配了，在做成交和委托匹配时有用。若成交单里含有委托合同编号，则不使用该字段。

        self.status = DyStockEntrust.Status.notDealed # 委托状态

        self.dyEntrustId = None # DevilYuan系统中的唯一委托编号，通常是broker.委托编号。委托编号为日期+计数，主要是考虑连续多日实盘的唯一性。
        self.brokerEntrustId = None # 券商的委托号

        self.strategyCls = None

        self.cancelDatetime = None # 撤销委托时间

        self.signalInfo = None # 策略委托的信号信息，回测时有效

    def isDone(self):
        if self.status in [DyStockEntrust.Status.allDealed, DyStockEntrust.Status.cancelled, DyStockEntrust.Status.discarded]:
            return True

        return False

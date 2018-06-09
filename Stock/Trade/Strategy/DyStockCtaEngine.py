from datetime import *
from time import sleep
from collections import OrderedDict

from DyCommon.DyCommon import *
from ...Common.DyStockCommon import *
from EventEngine.DyEvent import *
from ..DyStockTradeCommon import *
from ...Data.Engine.DyStockDataEngine import *
from ..DyStockStrategyBase import *
from .DyStockCtaBase import *
from .DyStockCtaEngineExtra import *
from ..Market.DyStockMarketFilter import *
from ..AccountManager.Broker.DyStockGtjaAccountManager import *
from ..AccountManager.Broker.DyStockYhAccountManager import *
from ..AccountManager.Broker.DyStockSimuAccountManager import *


class DyStockCtaEngine(object):
    """
        实盘CTA策略引擎
        一个账户可以绑定多个策略，行情推送顺序则由策略启动顺序决定
        Note: !!!所有关于策略和账户的操作只能由stockCtaEngine hand处理
    """

    accountManagerMap = {
                         'yh': DyStockYhAccountManager,
                         'simu1': DyStockSimuAccountManager1,
                         'simu2': DyStockSimuAccountManager2,
                         'simu3': DyStockSimuAccountManager3,
                         'simu4': DyStockSimuAccountManager4,
                         'simu5': DyStockSimuAccountManager5,
                         'simu6': DyStockSimuAccountManager6,
                         'simu7': DyStockSimuAccountManager7,
                         'simu8': DyStockSimuAccountManager8,
                         'simu9': DyStockSimuAccountManager9,
                         }


    class TimeState:
        nonTrade = 0
        callAuction = 1
        callAuctionBreak = 2
        morningTrade = 3
        morningTradeBreak = 4
        afternoonTrade = 5


    def __init__(self, dataEngine, eventEngine, info):
        self._dataEngine = dataEngine
        self._eventEngine = eventEngine
        self._info = info
        
        self._strategies = OrderedDict() # {strategyName: (strategy, DyStockMarketFilter)}, 策略的不同启动顺序决定了行情的推入顺序
        self._accountManagers = {} # {broker: account manager}
        self._strategyMirror = {} # 一键挂机时，交易日结束后的镜像，{strategyCls: strategy state}

        # 注册事件监听
        self._registerEvent()

        # error DataEngine
        # 有时策略@prepare需要独立载入大量个股数据，避免输出大量log
        errorInfo = DyErrorInfo(eventEngine)
        self._errorDataEngine = DyStockDataEngine(eventEngine, errorInfo, registerEvent=False)

        self._curInit()

    def _curInit(self):
        """
            当日相关数据的初始化
        """
        self._curDate = str(datetime.now().date()) # 当日，不是当前交易日

        self._barAggs = {} # {barMode: DyStockCtaBarAgg}
        self._timeState = self.TimeState.nonTrade # 时间状态

        # {strategyName: {code: [op]}}。策略没有绑定账户时的操作字典，避免没有绑定账户时同一操作重复发给UI，导致UI阻塞。
        # 比如，前一天策略在绑定账户时买入一股票，当天以监控方式运行该策略，恰巧这只股票要止损。这样可以避免这只股票的卖出操作重复发给UI。
        self._strategyNotBindAccountManagerOps = {}

        self._indexTick = None # 当前Tick，为沪市和深市的最新tick。回测没有此数据。
        self.__etf300Tick = None # 当前ETF300 Tick，主要为了实盘和回测的时间统一。也就是说，如果策略需要时间，一定要取ETF300。
        self.__etf500Tick = None

    @property
    def marketTime(self):
        return self._indexTick.time if self._indexTick else None

    @property
    def marketDatetime(self):
        return self._indexTick.datetime if self._indexTick else None

    @property
    def indexTick(self):
        return self._indexTick

    @property
    def etf300Tick(self):
        return self.__etf300Tick

    @property
    def etf500Tick(self):
        return self.__etf500Tick

    def _setTicks(self, ticks):
        """
            设置指数tick和ETF300/ETF500 tick。指数tick采用贪婪算法。
            @return: szIndexTick, shIndexTick
        """
        szIndexTick = ticks.get(DyStockCommon.szIndex)
        shIndexTick = ticks.get(DyStockCommon.shIndex)
        etf300Tick = ticks.get(DyStockCommon.etf300)
        etf500Tick = ticks.get(DyStockCommon.etf500)

        # set index tick with latest time
        if szIndexTick and shIndexTick:
            if szIndexTick.time > shIndexTick.time:
                self._indexTick = szIndexTick
            else:
                self._indexTick = shIndexTick

        elif szIndexTick:
            self._indexTick = szIndexTick
        elif shIndexTick:
            self._indexTick = shIndexTick
        else:
            if etf300Tick:
                self._indexTick = etf300Tick

        # set etf300 tick
        if etf300Tick:
            self.__etf300Tick = etf300Tick

        # set etf500 tick
        if etf500Tick:
            self.__etf500Tick = etf500Tick

        return szIndexTick, shIndexTick

    def _processTicks(self, ticks):
        """
            处理Ticks：
            - 检查是不是当日有效ticks
                - 开盘ticks
                - 交易时间的ticks
                - 不推送集合竞价ticks
            - 判断是不是收盘了，这样引擎可以调用策略的onClose
            @return: bool - valid ticks or not, bool - market close or not
        """
        # always set ticks firstly
        szIndexTick, shIndexTick = self._setTicks(ticks)

        if not DyStockTradeCommon.enableCtaEngineTickOptimization:
            return True, False

        # !!!由于沪市和深市更新频率不一样， 通常情况以上证指数和深圳成指最新时间为基准
        # 但判断上午收盘和下午收盘，则以最慢的时间为准。
        if not (szIndexTick and shIndexTick):
            return False, False

        time = self._indexTick.time

        # 时间状态机
        # 在不是非交易状态（TimeState.nonTrade），从效率考虑，时间只做单边判断。
        # 这样做看似不太严谨，比如在上午交易状态，若中间断网或其它原因，引擎收到下一个tick的时间直接跳到13:14:00，
        # 这个时候状态还是会经过TimeState.morningTradeBreak，然后到TimeState.afternoonTrade，只是这个状态变化需要下一个tick驱动。
        # 若没有下一个tick，状态会保持在TimeState.morningTradeBreak。
        # 也就是说在非交易状态，状态机的转换是按tick时间顺序来的。
        # !!!所以连续挂机，一定要每天做@_curInit以恢复每日状态。
        if self._timeState == self.TimeState.morningTrade: # 上午交易状态
            if szIndexTick.time >= '11:30:00' and shIndexTick.time >= '11:30:00':
                self._timeState = self.TimeState.morningTradeBreak
                return True, False

            return True, False

        elif self._timeState == self.TimeState.afternoonTrade: #下午交易状态
            if szIndexTick.time >= '15:00:00' and shIndexTick.time >= '15:00:00': # 收盘
                self._timeState = self.TimeState.nonTrade
                return True, True

            return True, False

        elif self._timeState == self.TimeState.callAuctionBreak: # 集合竞价后的休息状态
            if time >= '09:30:00':
                self._timeState = self.TimeState.morningTrade
                return True, False

            return False, False

        elif self._timeState == self.TimeState.morningTradeBreak: # 上午收盘后的状态
            if time >= '13:00:00':
                self._timeState = self.TimeState.afternoonTrade
                return True, False

            return False, False

        elif self._timeState == self.TimeState.callAuction: # 集合竞价状态
            if time >= '09:25:00': # 推送开盘ticks
                self._timeState = self.TimeState.callAuctionBreak
                return True, False

            return False, False

        else: # 非交易时间
            if self._curDate != szIndexTick.date:
                return False, False

            if '09:15:00' <= time < '09:25:00': # 集合竞价
                self._timeState = self.TimeState.callAuction
                return False, False

            elif '09:25:00' <= time < '09:30:00': # 集合竞价后的休息时间
                self._timeState = self.TimeState.callAuctionBreak
                return True, False

            elif '09:30:00' <= time < '11:30:00': # 上午交易时间
                self._timeState = self.TimeState.morningTrade
                return True, False

            elif '11:30:00' <= time < '13:00:00': # 上午交易休息时间
                self._timeState = self.TimeState.morningTradeBreak
                return True, False

            elif '13:00:00' <= time < '15:00:00': # 下午交易时间
                self._timeState = self.TimeState.afternoonTrade
                return True, False

            return False, False

    def _processClose(self):
        """
            收盘处理
        """
        self._info.print('股票CTA引擎: 收盘[{}]处理'.format(self._curDate), DyLogData.ind1)

        # 账户管理类
        for _, accountManager in self._accountManagers.items():
            accountManager.onClose()

        # call @onClose for each strategy
        for strategy, _ in self._strategies.values():
            strategy.onClose()

    #@DyTime.instanceTimeitWrapper
    def _stockMarketTicksHandler(self, event):
        """ 处理行情推送 """
        # unpack
        ticks = event.data

        # process ticks
        isValidTicks, isClose = self._processTicks(ticks)
        if not isValidTicks: # 无效Ticks
            return

        # 首先推送行情数据到账户管理实例。
        # 因为策略的有些仓位管理需要知道股票市值
        for _, accountManager in self._accountManagers.items():
            accountManager.onTicks(ticks)

        # bar聚合
        barsDict = {}
        for barMode, agg in self._barAggs.items():
            bars = agg.push(ticks)
            if bars is not None:
                barsDict[barMode] = bars

        # 推入数据到策略
        for strategy, filter in self._strategies.values():
            if strategy.liveMode == 'tick':
                filteredTicks = filter.filter(ticks)

                if filteredTicks:
                    strategy.onTicks(filteredTicks)

            else: # bar模式
                bars = barsDict.get(strategy.liveMode)

                if bars is not None:
                    filteredBars = filter.filter(bars)
                    if filteredBars:
                        strategy.onBars(filteredBars)

        # 处理收盘
        if isClose:
            self._processClose()
    
    def _startAccountManager(self, strategyCls):
        """
            启动策略的账户管理者
        """
        if strategyCls.broker is None:
            return True

        if strategyCls.broker not in self._accountManagers:
            # 实例化券商账户管理者
            accountManager = self.accountManagerMap[strategyCls.broker](self._eventEngine, self._info)

            # 账户管理的开盘前准备
            accountManager.onOpen(datetime.now().strftime("%Y-%m-%d"))

            self._accountManagers[strategyCls.broker] = accountManager

            # 登录策略的实盘交易接口
            event = DyEvent(DyEventType.stockLogin)
            event.data['broker'] = strategyCls.broker

            self._eventEngine.put(event)

        self._info.print('股票CTA引擎: 账号[{0}]绑定策略[{1}]'.format(self.accountManagerMap[strategyCls.broker].brokerName, strategyCls.chName), DyLogData.ind1)

        return True

    def _getAccountManager(self, strategyCls):
        """
            获取指定策略绑定到的账户管理实例
        """
        accountManager = self._accountManagers.get(strategyCls.broker)
        if accountManager is None:
            return None

        strategyTuple = self._strategies.get(strategyCls.name)
        if strategyTuple is None:
            return None

        strategy = strategyTuple[0]
        if strategy.state.isState(DyStockStrategyState.running):
            return accountManager

        return None

    def _stopAccountManager(self, strategyCls, oneKeyHangUp=False):
        """
            停止策略的账户管理者
            @oneKeyHangUp: 一键挂机导致的
        """
        if strategyCls.broker is None:
            return

        if strategyCls.broker not in self._accountManagers:
            return

        self._info.print('股票CTA引擎: 账号[{0}]解除绑定策略[{1}]'.format(self.accountManagerMap[strategyCls.broker].brokerName, strategyCls.chName), DyLogData.ind1)

        # check if other running strategies use the same account manager
        for strategy, _ in self._strategies.values():
            if strategy.name != strategyCls.name and \
                strategyCls.broker == strategy.broker and \
                strategy.state.isState(DyStockStrategyState.running):
                return

        # 退出策略的实盘交易接口
        event = DyEvent(DyEventType.stockLogout)
        event.data['broker'] = strategyCls.broker
        event.data['oneKeyHangUp'] = oneKeyHangUp

        self._eventEngine.put(event)

        # 销毁券商账户管理者
        self._accountManagers[strategyCls.broker].exit()
        del self._accountManagers[strategyCls.broker]

    def _updateStrategyAccount(self, strategy):
        """
            向UI推送策略的账户相关事件
            只有不改变的对象内容可以在多线程之间传递。策略账户相关的对象可能会改变，所以做deepcopy或者copy
        """
        # 持仓
        self._updateStrategyPos(strategy)

        # 委托
        event = DyEvent(DyEventType.stockStrategyEntrustsUpdate + strategy.name)
        event.data = copy.deepcopy(strategy.curEntrusts)

        self._eventEngine.put(event)

        # 成交
        event = DyEvent(DyEventType.stockStrategyDealsUpdate + strategy.name)
        event.data = list(strategy.curDeals.values()) # [DyStockDeal]

        self._eventEngine.put(event)

    def _startStockCtaStrategyHandler(self, event):
        """ 启动策略, 创建唯一策略实例 """
        strategyCls = event.data['class']
        state = event.data['state']

        self._info.print('开始启动策略: {0}, 状态: {1},...'.format(strategyCls.chName, state.state), DyLogData.ind)

        #　是否是唯一策略实例
        if strategyCls.name in self._strategies:
            self._info.print('重复启动策略: {0}'.format(strategyCls.chName), DyLogData.error)
            return

        # !!!It's tricky for live trading but not accurate.
        sleep(1) # sleep so that UI related dynamic windows can be created firstly.

        # 实例化策略
        strategy = strategyCls(self, self._info, state)

        # 策略开盘前初始化
        if not strategy.onOpen(datetime.now().strftime("%Y-%m-%d"), strategy.onOpenCodes()):
            self._info.print('策略: {0}启动失败'.format(strategyCls.chName), DyLogData.error)
            return

        # 启动策略的账户管理
        if state.isState(DyStockStrategyState.running):
            if strategy.broker is not None: # Strategy has configured the broker
                if not self._startAccountManager(strategyCls):
                    return

                # 从券商管理类同步策略持仓
                self._accountManagers[strategy.broker].syncStrategyPos(strategy)
        
        # 获取策略要监控的股票池
        monitoredStocks = strategy.onMonitor()

        # 添加到策略字典
        self._strategies[strategyCls.name] = (strategy, DyStockMarketFilter(monitoredStocks))

        # 添加到bar聚合字典
        if 'bar' in strategyCls.liveMode:
            if strategyCls.liveMode not in self._barAggs:
                self._barAggs[strategyCls.liveMode] = DyStockCtaBarAggFast(strategyCls.liveMode, monitoredStocks)
            else:
                self._barAggs[strategyCls.liveMode].add(monitoredStocks)

        # 向股票市场发送监控的股票池
        monitoredStocks = monitoredStocks + [DyStockCommon.etf300, DyStockCommon.etf500] # always add ETF300 and ETF500 for 大盘参考。主要原因是历史分笔数据没有指数的，所以只能用ETF替代。
        if monitoredStocks:
            event = DyEvent(DyEventType.stockMarketMonitor)
            event.data = monitoredStocks

            self._eventEngine.put(event)

        # 向UI推送策略的账户相关事件
        self._updateStrategyAccount(strategy)

        self._info.print('策略: {0}启动成功'.format(strategyCls.chName), DyLogData.ind)

    def _stopStockCtaStrategyHandler(self, event):
        """ 停止策略 """
        strategyCls = event.data['class']
        oneKeyHangUp = True if event.data.get('oneKeyHangUp') else False

        del self._strategies[strategyCls.name]

        self._stopAccountManager(strategyCls, oneKeyHangUp)

    def _changeStockCtaStrategyStateHandler(self, event):
        """ 改变策略状态 """
        strategyCls = event.data['class']
        newState = event.data['state']
        
        if strategyCls.name in self._strategies:
            strategy, _ = self._strategies[strategyCls.name]

            # 只考虑两种状态改变: 运行 -> 监控 或者 监控 -> 运行
            if strategy.state.isState(DyStockStrategyState.running) and \
                (newState.isState(DyStockStrategyState.monitoring) and not newState.isState(DyStockStrategyState.running)):

                self._stopAccountManager(strategyCls)

            elif (strategy.state.isState(DyStockStrategyState.monitoring) and not strategy.state.isState(DyStockStrategyState.running)) and \
                newState.isState(DyStockStrategyState.running):

                self._startAccountManager(strategyCls)

                # 从券商管理类同步策略持仓
                self._accountManagers[strategy.broker].syncStrategyPos(strategy)

                # 向UI推送策略的账户相关事件
                self._updateStrategyAccount(strategy)

            # 设置策略新的状态
            strategy.state = newState

        elif strategyCls in self._strategyMirror:
            self._strategyMirror[strategyCls] = newState

        else:
            self._info.print('股票CTA引擎: 改变策略[{}]状态错误'.format(strategyCls.chName), DyLogData.error)

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockMarketTicks, self._stockMarketTicksHandler, DyStockTradeEventHandType.stockCtaEngine)

        self._eventEngine.register(DyEventType.startStockCtaStrategy, self._startStockCtaStrategyHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.register(DyEventType.stopStockCtaStrategy, self._stopStockCtaStrategyHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.register(DyEventType.changeStockCtaStrategyState, self._changeStockCtaStrategyStateHandler, DyStockTradeEventHandType.stockCtaEngine)

        # 一键挂机相关事件
        self._eventEngine.register(DyEventType.beginStockTradeDay, self._beginStockTradeDayHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.register(DyEventType.endStockTradeDay, self._endStockTradeDayHandler, DyStockTradeEventHandType.stockCtaEngine)

        # 交易接口的委托和成交回报事件
        self._eventEngine.register(DyEventType.stockOnEntrust, self._stockOnEntrustHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.register(DyEventType.stockOnDeal, self._stockOnDealHandler, DyStockTradeEventHandType.stockCtaEngine)

        # 券商账户的股票持仓更新事件
        self._eventEngine.register(DyEventType.stockOnPos, self._stockOnPosHandler, DyStockTradeEventHandType.stockCtaEngine)

        # 来自账户管理类的股票持仓同步事件
        self._eventEngine.register(DyEventType.stockPosSyncFromAccountManager, self._stockPosSyncFromAccountManagerHandler, DyStockTradeEventHandType.stockCtaEngine)

        # 策略手工买入相关事件
        self._eventEngine.register(DyEventType.stockStrategyMonitoredCodesReq, self._stockStrategyMonitoredCodesReqHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.register(DyEventType.stockStrategyManualBuy, self._stockStrategyManualBuyHandler, DyStockTradeEventHandType.stockCtaEngine)

        # 策略手工卖出相关事件
        self._eventEngine.register(DyEventType.stockStrategyPosReq, self._stockStrategyPosReqHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.register(DyEventType.stockStrategyManualSell, self._stockStrategyManualSellHandler, DyStockTradeEventHandType.stockCtaEngine)

    def _beginStockTradeDayHandler(self, event):
        if self._strategyMirror and not self._strategies:
            # init
            self._curInit()

            self._info.print('股票CTA引擎: 开始交易日[{}]'.format(self._curDate), DyLogData.ind2)

            # start strategies
            for strategyCls, state in self._strategyMirror.items():
                event = DyEvent(DyEventType.startStockCtaStrategy)
                event.data['class'] = strategyCls
                event.data['state'] = state

                self._startStockCtaStrategyHandler(event)

            self._strategyMirror = {}

    def _endStockTradeDayHandler(self, event):
        if not self._strategyMirror and self._strategies:
            self._info.print('股票CTA引擎: 结束交易日[{}]'.format(self._curDate), DyLogData.ind2)

            # save strategies and stop strategy running
            for strategy, _ in self._strategies.values():
                # save
                self._strategyMirror[strategy.__class__] = strategy.state

                # stop
                event = DyEvent(DyEventType.stopStockCtaStrategy)
                event.data['class'] = strategy.__class__
                event.data['oneKeyHangUp'] = True

                self._stopStockCtaStrategyHandler(event)

    def _stockStrategyMonitoredCodesReqHandler(self, event):
        strategyCls = event.data

        if strategyCls.name not in self._strategies:
            return

        filter = self._strategies[strategyCls.name][1]

        event = DyEvent(DyEventType.stockStrategyMonitoredCodesAck)
        event.data = filter.codes

        self._eventEngine.put(event)

    def _stockStrategyManualBuyHandler(self, event):
        # unpack
        strategyCls = event.data['class']
        tick = event.data['tick']
        volume = event.data['volume']
        price = event.data['price']

        strategy = self._strategies[strategyCls.name][0]

        # buy
        if strategy.buy(tick, volume, price=price):
            self._info.print('策略[{0}] - 手工买入, {1}[{2}], {3}股, 价格{4}: 成功'.format(strategy.chName, tick.code, tick.name, volume, price), DyLogData.ind1)
        else:
            self._info.print('策略[{0}] - 手工买入, {1}[{2}], {3}股, 价格{4}: 失败'.format(strategy.chName, tick.code, tick.name, volume, price), DyLogData.error)

    def _stockStrategyPosReqHandler(self, event):
        strategyCls = event.data

        if strategyCls.name not in self._strategies:
            return

        strategy = self._strategies[strategyCls.name][0]

        event = DyEvent(DyEventType.stockStrategyPosAck)
        event.data = strategy.curPos

        self._eventEngine.put(event)

    def _stockStrategyManualSellHandler(self, event):
        # unpack
        strategyCls = event.data['class']
        tick = event.data['tick']
        volume = event.data['volume']
        price = event.data['price']

        strategy = self._strategies[strategyCls.name][0]

        # buy
        if strategy.sell(tick, volume, sellReason=DyStockSellReason.manualSell, price=price):
            self._info.print('策略[{0}] - 手工卖出, {1}[{2}], {3}股, 价格{4}: 成功'.format(strategy.chName, tick.code, tick.name, volume, price), DyLogData.ind1)
        else:
            self._info.print('策略[{0}] - 手工卖出, {1}[{2}], {3}股, 价格{4}: 失败'.format(strategy.chName, tick.code, tick.name, volume, price), DyLogData.error)

    def _stockOnPosHandler(self, event):
        """
            券商账户的股票持仓更新事件
        """
        # unpack
        broker = event.data['broker']
        positions = event.data['pos']

        for strategy, _ in self._strategies.values():
            if strategy.broker != broker:
                continue

            strategy.onPos(positions)

            # 向UI推送更新
            self._updateStrategyPos(strategy)

    def _stockPosSyncFromAccountManagerHandler(self, event):
        """
            来自账户管理类的股票持仓同步事件
        """
        # unpack
        broker = event.data['broker']
        syncData = event.data['data']

        self._info.print('股票CTA引擎: 账户[{0}]持仓同步完成'.format(self.accountManagerMap[broker].brokerName), DyLogData.ind1)

        for strategy, _ in self._strategies.values():
            if strategy.broker != broker:
                continue

            strategy.syncPos(syncData)

    def _stockOnEntrustHandler(self, event):
        """
            券商委托回报处理
        """
        # unpack
        entrusts = event.data

        for entrust in entrusts:
            strategyTuple = self._strategies.get(entrust.strategyCls.name)
            if strategyTuple is None:
                continue

            strategy, _ = strategyTuple

            # push to strategy
            strategy.onEntrust(copy.copy(entrust))

            # put UI event
            # This is entrust from broker pushing, so it should be already existing in DevilYuan system.
            self._updateStrategyEntrust(entrust)

    def _stockOnDealHandler(self, event):
        """
            券商成交回报处理
        """
        # unpack
        deals = event.data

        strategies = set() # set of strategy which has deals from broker pushing

        for deal in deals:
            strategyTuple = self._strategies.get(deal.strategyCls.name)
            if strategyTuple is None:
                continue

            strategy, _ = strategyTuple

            # push to strategy
            strategy.onDeal(deal)

            # save
            strategies.add(strategy)

            # put UI event
            self._updateStrategyDeal(deal)

        # Deal should impact positions, so put UI strategy positions update event
        for strategy in strategies:
            self._updateStrategyPos(strategy)

    def putStockMarketStrengthUpdateEvent(self, strategyCls, time, marketStrengthInfo):
        event = DyEvent(DyEventType.stockMarketStrengthUpdate)
        event.data['class'] = strategyCls
        event.data['time'] = time
        event.data['data'] = marketStrengthInfo

        self._eventEngine.put(event)

    def putEvent(self, type, data):
        """
            推送一个事件到事件引擎
            @type: 事件类型
            @data: 事件数据，一般为dict
        """
        event = DyEvent(type)
        event.data = data

        self._eventEngine.put(event)

    def putStockMarketMonitorUiEvent(self, strategyCls, data=None, newData=False, op=None, signalDetails=None, datetime_=None):
        """
            触发策略行情监控事件(通常用于通知GUI更新)
            @strategyCls: strategy class
            @data: 策略显示数据, [[]]
            @newData: True-策略显示数据是全新的数据，False-只是更新策略显示数据
            @op: 策略操作数据, [[]]。
                 若策略是运行状态（实盘状态）并且绑定券商账户，则op是实盘操作。若策略是监控状态或者没有绑定券商账户，则op就是非实盘操作。
                 其实非实盘时，可以不向UI推送操作，这么做只是为了非真正实盘时，能看到策略的操作明细。
                 信号明细和操作明细是不同的，有信号未必就会有操作，因为实盘时的操作牵涉到风控和资金管理。
            @signalDetails: 策略信号明细数据, [[]]
            @datetime_: 行情数据时有效
        """
        event = DyEvent(DyEventType.stockMarketMonitorUi + strategyCls.name)

        # data
        if data:
            event.data['data'] = {'data': data,
                                  'new': newData,
                                  'datetime': datetime_
                                  }

        # indication
        ind = {}
        if op:
            ind['op'] = op

        if signalDetails:
            ind['signalDetails'] = signalDetails

        if ind:
            event.data['ind'] = ind

        # put event
        if event.data:
            event.data['class'] = strategyCls
            self._eventEngine.put(event)

    def tLatestDayInDb(self):
        return self._dataEngine.daysEngine.tLatestDayInDb()

    def tDaysOffsetInDb(self, base, n=0):
        return self._dataEngine.daysEngine.tDaysOffsetInDb(base, n)

    def loadPreparedData(self, date, strategyCls):
        """
            从磁盘载入实盘策略的准备数据
            @date: 当日
        """
        # 用户没有通过UI指定策略准备数据的日期, 即前一交易日
        if DyStockTradeCommon.strategyPreparedDataDay is None:
            assert(date == datetime.now().strftime("%Y-%m-%d"))

            date = self.tDaysOffsetInDb(DyTime.getDateStr(date, -1))
            if date is None:
                self._info.print('股票历史日线数据缺失', DyLogData.error)
                return None
        else:
            date = DyStockTradeCommon.strategyPreparedDataDay

        path = DyCommon.createPath('Stock/Program/Strategy/{}/{}'.format(strategyCls.chName, date))
        fileName = os.path.join(path, 'preparedData.json')

        try:
            with open(fileName) as f:
                data = json.load(f)

                return data

        except:
            pass

        return None

    def loadPreparedPosData(self, date, strategyCls):
        """
            从磁盘载入实盘策略的持仓准备数据
            @date: 当日
        """
        # 用户没有通过UI指定策略准备数据的日期, 即前一交易日
        if DyStockTradeCommon.strategyPreparedDataDay is None:
            assert(date == datetime.now().strftime("%Y-%m-%d"))

            date = self.tDaysOffsetInDb(DyTime.getDateStr(date, -1))
            if date is None:
                self._info.print('股票历史日线数据缺失', DyLogData.error)
                return None
        else:
            date = DyStockTradeCommon.strategyPreparedDataDay

        # load from file
        path = DyCommon.createPath('Stock/Program/Strategy/{}/{}'.format(strategyCls.chName, date))
        fileName = os.path.join(path, 'preparedPosData.json')

        try:
            with open(fileName) as f:
                data = json.load(f)

                return data

        except:
            pass

        return None

    def loadOnClose(self, date, strategyCls):
        """
            载入策略收盘后保存的数据，用来恢复策略实例状态
            @date: 当日
        """
        # 用户没有通过UI指定策略准备数据的日期, 即前一交易日或者当日（如果已经收盘），优先当日。
        if DyStockTradeCommon.strategyPreparedDataDay is None:
            dates = [date, self.tDaysOffsetInDb(DyTime.getDateStr(date, -1))]
        else:
            dates = [DyStockTradeCommon.strategyPreparedDataDay]

        path = DyCommon.createPath('Stock/Program/Strategy/{}'.format(strategyCls.chName))

        for date in dates:
            fileName = os.path.join(path, date, 'savedData.json')

            try:
                with open(fileName) as f:
                    savedData = json.load(f)

                    return savedData

            except Exception as ex:
                pass

        return None

    def saveOnClose(self, date, strategyCls, savedData=None):
        """
            保存策略收盘后的数据，用来恢复策略实例状态
            @date: 当日
        """
        if not savedData:
            return

        path = DyCommon.createPath('Stock/Program/Strategy/{}/{}'.format(strategyCls.chName, date))
        fileName = os.path.join(path, 'savedData.json')
        with open(fileName, 'w') as f:
            f.write(json.dumps(savedData, indent=4, cls=DyJsonEncoder))

    def _updateStrategyEntrust(self, entrust):
        """
            向UI推送策略委托事件
        """
        # because only one entrust, no need OrderedDict
        event = DyEvent(DyEventType.stockStrategyEntrustsUpdate + entrust.strategyCls.name)
        event.data = {entrust.dyEntrustId: copy.copy(entrust)}

        self._eventEngine.put(event)

    def _updateStrategyDeal(self, deal):
        """
            向UI推送策略成交事件
        """
        event = DyEvent(DyEventType.stockStrategyDealsUpdate + deal.strategyCls.name)
        event.data = [deal]

        self._eventEngine.put(event)

    def _updateStrategyPos(self, strategy):
        """
            向UI推送策略持仓更新事件
        """
        # 持仓
        event = DyEvent(DyEventType.stockStrategyPosUpdate + strategy.name)
        event.data = copy.deepcopy(strategy.curPos)

        self._eventEngine.put(event)

    def _isInStrategyNotBindAccountManagerOps(self, strategyCls, op):
        """
            Check if op is already existing in condition strategy not bind account manager.
            If not existing, add it.
            @op: [x, x, x, ...]
        """
        ops = self._strategyNotBindAccountManagerOps.setdefault(strategyCls.name, {})

        code = op[strategyCls.opHeaderCodePos]
        opList = ops.setdefault(code, [])

        for op_ in opList:
            if op_[1:] == op[1:]: # not consider datetime at 0 position.
                return True

        opList.append(op)
        return False
        
    def buy(self, strategyCls, tick, volume, signalInfo=None, price=None):
        """
            @return: DyStockEntrust object or None
        """
        datetime = tick.datetime
        code = tick.code
        name = tick.name
        if price is None:
            price = getattr(tick, strategyCls.buyPrice)

        ret = True
        
        accountManager = self._getAccountManager(strategyCls)
        if accountManager: # 策略已经绑定实盘账户
            ret = accountManager.buy(datetime, strategyCls, code, name, price, volume, signalInfo)
            if ret: # entrust, so put event to UI
                self._updateStrategyEntrust(ret)

        if ret: # 委托成功或者策略处于监控状态
            op = [[datetime.strftime('%Y-%m-%d %H:%M:%S'), '买入', code, name, price, volume, None, None, None, None]]

            if accountManager:
                self.putStockMarketMonitorUiEvent(strategyCls, op=op)
            else:
                if not self._isInStrategyNotBindAccountManagerOps(strategyCls, op[0]):
                    self.putStockMarketMonitorUiEvent(strategyCls, op=op)

            if ret is True:
                ret = None

        return ret

    def _getCodeSellPnl(self, accountManager, code, price, volume):
        """
            获取股票卖出时的收益
        """
        cost, pnlRatio, pnl = None, None, None
        if accountManager:
            cost = accountManager.getCurCodePosCost(code)

        if cost is not None:
            if cost > 0:
                pnlRatio = (price - cost)/cost*100

            pnl = (price - cost)*volume

        return cost, pnlRatio, pnl

    def sell(self, strategyCls, tick, volume, sellReason=None, signalInfo=None, price=None):
        """
            @return: DyStockEntrust object or None
        """
        datetime = tick.datetime
        code = tick.code
        name = tick.name
        if price is None:
            price = getattr(tick, strategyCls.sellPrice)

        ret = True

        accountManager = self._getAccountManager(strategyCls)
        if accountManager:
            ret = accountManager.sell(datetime, strategyCls, code, price, volume, sellReason, signalInfo)
            if ret: # entrust, so put event to UI
                self._updateStrategyEntrust(ret)

        if ret:
            # get pnl related for sell code
            cost, pnlRatio, pnl = self._getCodeSellPnl(accountManager, code, price, volume)

            op = [[datetime.strftime('%Y-%m-%d %H:%M:%S'), '卖出', code, name, price, volume, sellReason, cost, pnlRatio, pnl]]

            if accountManager:
                self.putStockMarketMonitorUiEvent(strategyCls, op=op)
            else:
                if not self._isInStrategyNotBindAccountManagerOps(strategyCls, op[0]):
                    self.putStockMarketMonitorUiEvent(strategyCls, op=op)

            if ret is True:
                ret = None

        return ret

    def cancel(self, strategyCls, cancelEntrust):
        """
            策略撤销委托
        """
        accountManager = self._getAccountManager(strategyCls)
        if accountManager:
            return accountManager.cancel(cancelEntrust)

        return False

    def closePos(self, strategyCls, tick, volume, sellReason, signalInfo=None):
        """
            @return: DyStockEntrust object or None
        """
        datetime = tick.datetime
        code = tick.code
        name = tick.name
        price = getattr(tick, strategyCls.sellPrice)

        ret = True

        accountManager = self._getAccountManager(strategyCls)
        if accountManager:
            # 不调用账户管理类的closePos，因为是单账户多策略
            ret = accountManager.sell(datetime, strategyCls, code, price, volume, sellReason, signalInfo)
            if ret: # entrust, so put event to UI
                self._updateStrategyEntrust(ret)

        if ret:
            # get pnl related for sell code
            cost, pnlRatio, pnl = self._getCodeSellPnl(accountManager, code, price, volume)

            op = [[datetime.strftime('%Y-%m-%d %H:%M:%S'), '卖出', code, name, price, '清仓(%.3f)'%volume, sellReason, cost, pnlRatio, pnl]]

            if accountManager:
                self.putStockMarketMonitorUiEvent(strategyCls, op=op)
            else:
                if not self._isInStrategyNotBindAccountManagerOps(strategyCls, op[0]):
                    self.putStockMarketMonitorUiEvent(strategyCls, op=op)

            if ret is True:
                ret = None

        return ret

    def buyByRatio(self, strategyCls, tick, ratio, ratioMode, signalInfo=None):
        return DyStockCtaEngineExtra.buyByRatio(self, self._getAccountManager(strategyCls), strategyCls, tick, ratio, ratioMode, signalInfo)

    def sellByRatio(self, strategy, tick, ratio, ratioMode, sellReason=None, signalInfo=None):
        return DyStockCtaEngineExtra.sellByRatio(self, self._getAccountManager(strategy.__class__), strategy, tick, ratio, ratioMode, sellReason, signalInfo)

    def getBuyVol(self, cash, code, price):
        return DyStockTradeCommon.getBuyVol(cash, code, price)

    @property
    def dataEngine(self):
        return self._dataEngine

    @property
    def errorDataEngine(self):
        return self._errorDataEngine

    def getCurPos(self, strategyCls):
        """
            这里并不关心策略的运行状态，只是返回对应账户的数据
        """
        if strategyCls.broker in self._accountManagers:
            return self._accountManagers[strategyCls.broker].curPos

        return None

    def getCurCash(self, strategyCls):
        """
            这里并不关心策略的运行状态，只是返回对应账户的数据
        """
        if strategyCls.broker in self._accountManagers:
            return self._accountManagers[strategyCls.broker].curCash

        return None

    def getCurCapital(self, strategyCls):
        """
            这里并不关心策略的运行状态，只是返回对应账户的数据
        """
        if strategyCls.broker in self._accountManagers:
            return self._accountManagers[strategyCls.broker].getCurCapital()

        return None

    def getCurCodePosMarketValue(self, strategyCls, code):
        if strategyCls.broker in self._accountManagers:
            return self._accountManagers[strategyCls.broker].getCurCodePosMarketValue(code)

        return None

    def getCurPosMarketValue(self, strategyCls):
        if strategyCls.broker in self._accountManagers:
            return self._accountManagers[strategyCls.broker].getCurPosMarketValue()

        return None


class DyStockCtaBarAgg:
    """
        股票实时K线聚合
        !!!没有测试过
    """
    def __init__(self, barMode, codes):
        """
            @barMode: 'bar1s', 'bar1m', 'bar1h'
            @codes: [code]，需要聚合的代码
        """
        unit = barMode[-1]
        if unit == 's':
            factor = 1
        elif unit == 'm':
            factor = 60
        else:
            factor = 3600

        self._barWidth = int(barMode[3:-1])*factor # unit is second

        self._barTicks = {code: [None, [], None] for code in codes} # {code: [bar index, [bar tick], last tick of previous bar]}

    def _convert2Sec(self, tick):
        """
            Note: !!!It'tricky that '11:30:00' and '13:00:00' have same converted seconds.
            We think 2*3600 as '11:30:00', according to aggregate algorithm, '13:00:00' is included in the first bar of the afternoon.
            实盘时，'15:00:00'之后的tick不会生成bar
        """
        # adjust time of tick
        time = tick.time

        if '09:30:00'> time >= '09:25:00':
            time = '09:30:00'
        elif '11:30:05'>= time > '11:30:00':
            time = '11:30:00'
        elif '15:00:05'>= time > '15:00:00':
            time = '15:00:00'

        # convert
        if '11:30:00' >= time >= '09:30:00':
            s = int(time[:2] - 9)*3600 + int(time[3:5] - 30)*60 + int(time[-2:])
        elif '15:00:00' >= time >= '13:00:00':
            s = int(time[:2] - 13)*3600 + int(time[3:5])*60 + int(time[-2:]) + 2*3600
        else:
            return None

        return s

    def _convert2Time(self, barIndex):
        s = barIndex*self._barWidth

        if s <= 2*3600:
            startTimeH = 9
            s += 30*60 # align with hour
        else:
            startTimeH = 13

        h = s//3600
        m = (s%3600)/60
        s = (s%3600)%60

        # adjust hour
        h += startTimeH

        return '{0}:{1}:{2}'.format(h if h > 9 else ('0' + str(h)), m if m > 9 else ('0' + str(m)), s if s > 9 else ('0' + str(s)))

    def _agg(self, barTicks, barNo):
        """
            bar聚合
            @barNo: bar编号，从1开始，new bar index即为当前要聚合bar的编号
        """
        if not barTicks:
            return None

        # bar的时间，右边界时间
        barTime = self._convert2Time(barNo)

        tick = barTicks[1][0]

        barData = DyStockCtaBarData()

        barData.code = code
        barData.name = name

        # OHLC
        barData.open = barTicks[1][0].price
        barData.high = max(barTicks[1])
        barData.low = min(barTicks[1])
        barData.close = barTicks[1][-1].price

        barData.preClose = tick.preClose

        barData.date = tick.date
        barData.time = barTime
        barData.datetime = datetime.strptime(tick.date + ' ' + barTime, '%Y-%m-%d %H:%M:%S')

        # volume(单位: 股数，不是手)
        if barTicks[2] is None:
            if barNo == 1:
                lastTickVolumeOfPreBar = 0
            else:
                lastTickVolumeOfPreBar = barTicks[1][0].volume
        else:
            lastTickVolumeOfPreBar = barTicks[2].volume

        barData.volume = barTicks[1][-1].volume - lastTickVolumeOfPreBar

        return barData

    def add(self, codes):
        """
            添加代码
            @codes: [code]
        """
        for code in codes:
            self._barTicks.setdefault(code, [None, [], None])

    def push(self, ticks):
        """
            推入ticks
            @ticks: {code: DyStockTickData}
            @return: {code: DyStockBarData}
        """
        s = None
        bars = {}
        for code, barTicks in self._barTicks.items():
            tick = ticks.get(code, None)
            if tick is None:
                continue

            if s is None: # 任选一个tick的时间
                s = self._convert2Sec(tick)
                newBarIndex = s//self._barWidth

            # 初始化bar index
            # 如果tick正好是bar的右边界，这个tick则会归为下个bar
            # 这样对'09:30:00'的tick，不会被归为bar的右边界
            # 由于'09:30:00'和'13:00:00'有相同的converted secnods，所以'13:00:00'的tick，不会被归为bar的右边界
            if barTicks[0] is None:
                barTicks[0] = newBarIndex

            # bar index相等，则为同一个bar
            if newBarIndex == barTicks[0]:
                barTicks[1].append(tick)

            else:
                # bar的右边界tick
                if s%self._barWidth == 0:
                    barTicks[1].append(tick)

                # bar聚合
                barData = self._agg(barTicks, newBarIndex)
                if barData is not None:
                    bars[code] = barData

                # new bar
                barTicks[0] = newBarIndex
                barTicks[2] = None if barTicks[1] is None else barTicks[1][-1] # last tick of previous bar
                barTicks[1] = []

                # tick for new bar
                if s%self._barWidth > 0:
                    barTicks[1].append(tick)

        return bars if bars else None


class DyStockCtaBarAggFast:
    """
        股票实时K线快速聚合, 只支持分钟聚合
        Bar的时间为第一个Tick的时间。左边界聚合方式。
    """
    def __init__(self, barMode, codes):
        """
            @barMode: 'bar1m'
            @codes: [code]，需要聚合的代码
        """
        unit = barMode[-1]
        assert unit == 'm'

        self._barWidth = int(barMode[3:-1])

        self._bars = {code: [None, None] for code in codes} # {code: [current bar, previous tick]}

    def add(self, codes):
        """
            添加代码
            @codes: [code]
        """
        for code in codes:
            self._bars.setdefault(code, [None, None])

    def _createBar(self, refTick, tick, volume=0):
        bar = DyStockCtaBarData()

        bar.code = tick.code
        bar.name = tick.name

        # OHLC
        bar.open = tick.price
        bar.high = tick.price
        bar.low = tick.price
        bar.close = tick.price

        bar.preClose = tick.preClose

        bar.date = refTick.date
        bar.time = refTick.time
        bar.datetime = refTick.datetime

        bar.volume = volume

        return bar

    def _createRefTick(self, tick):
        # adjust time of tick
        time = tick.time

        if '09:30:00'> time >= '09:25:00':
            time = '09:25:00'
        elif '11:30:05'>= time > '11:30:00':
            time = '11:30:00'
        elif '15:00:05'>= time > '15:00:00':
            time = '15:00:00'
        elif '11:30:00' >= time >= '09:30:00' or '15:00:00' >= time >= '13:00:00':
            pass
        else:
            return None

        refTick = DyStockCtaTickData()

        refTick.date = tick.date
        refTick.time = time
        refTick.datetime = datetime.strptime(refTick.date + ' ' + refTick.time, '%Y-%m-%d %H:%M:%S')
        
        return refTick

    def push(self, ticks):
        """
            推入ticks
            @ticks: {code: DyStockTickData}
            @return: {code: DyStockBarData}
        """
        refTick = None
        bars = {}
        for code, (bar, preTick) in self._bars.items():
            tick = ticks.get(code, None)
            if tick is None:
                continue

            if refTick is None: # 任选一个tick
                refTick = self._createRefTick(tick)
                if refTick is None: # 非交易时间
                    continue

            if bar is None:
                bar = self._createBar(refTick, tick)
                self._bars[code][0] = bar

            # bar已经生成
            if bar.datetime.minute != refTick.datetime.minute and \
                refTick.datetime.minute%self._barWidth == 0:

                # 已经聚合好的bar
                bar.bidPrices = tick.bidPrices # 为了实盘交易时的卖出价
                bar.askPrices = tick.askPrices # 为了实盘交易时的买入价
                bars[code] = bar

                # 开始新bar
                self._bars[code][0] = self._createBar(refTick, tick, tick.volume - preTick.volume)

            else: # 聚合bar
                bar.high = max(tick.price, bar.high)
                bar.low = min(tick.price, bar.low)
                bar.close = tick.price

                if preTick is None:
                    if refTick.time < '09:30:00':
                        preVolume = 0
                    else: # 交易时间
                        preVolume = tick.volume
                else:
                    preVolume = preTick.volume

                bar.volume += tick.volume - preVolume

            # at last, save previous tick for each code
            self._bars[code][1] = tick

        return bars if bars else None

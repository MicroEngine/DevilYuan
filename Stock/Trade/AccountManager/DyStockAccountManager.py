import os
import json
import copy
from collections import OrderedDict

from DyCommon.DyCommon import *
from ..DyStockTradeCommon import *
from EventEngine.DyEvent import *
from .DyStockPos import *
from ...Trade.Market.DyStockMarketFilter import *


class DyStockAccountManager:
    """
        实盘股票账户管理，主要对接券商接口。
        根据情况，从券商接口同步可用资金和持仓信息
        从风控和简化处理角度，禁止不同策略同一时间同一只股票相同委托类型的委托。成交的委托不在考虑之内。

        !!!由于持仓，委托对象可能会被多线程读写，所以事件引擎里传递的此类对象一定要copy。
        成交对象由于生成后不会改变，则无需copy。

        实盘账户管理，暂时并不支持停损模块。这个跟回测有区别。所以若策略要使用停损算法，则需要策略里实现。
        账户管理类的行情推送则由CTA引擎负责。

        *****************************************************
        !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ***!!!由于除复权，所以需要从券商接口同步持仓因子。
        如果交易不是通过策略，或者持仓同步不是在开盘时，可能会导致信息不一致或者错误。
        比如通过直接通过券商接口卖出策略的持仓股票，这时策略并不知道。
        对于模拟账户，因为除复权是根据行情推算出来的，所以9:15:00 - 9:30:00之间，策略的持仓可能是没有除复权过。
        所以策略在这个时间段的操作可能会有问题。
    """
    broker = None
    brokerName = None

    riskGuardNbr = 5 # 暂时没有启用此功能


    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._riskGuardNbr = self.riskGuardNbr
        self._riskGuardCount = 0 # 一旦发生某些原因(清仓)的closePos，则进行风控，也就是说@self._riskGuardNbr个交易日内禁止买入

        self._curInit()

        self._registerEvent()

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockCapitalUpdate + self.broker, self._stockCapitalUpdateHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.register(DyEventType.stockPositionUpdate + self.broker, self._stockPositionUpdateHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.register(DyEventType.stockCurEntrustsUpdate + self.broker, self._stockCurEntrustsUpdateHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.register(DyEventType.stockCurDealsUpdate + self.broker, self._stockCurDealsUpdateHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.register(DyEventType.stockEntrustUpdate + self.broker, self._stockEntrustUpdateHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.register(DyEventType.stockPosSyncFromBroker + self.broker, self._stockPosSyncFromBrokerHandler, DyStockTradeEventHandType.stockCtaEngine)

    def _unregisterEvent(self):
        self._eventEngine.unregister(DyEventType.stockCapitalUpdate + self.broker, self._stockCapitalUpdateHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.unregister(DyEventType.stockPositionUpdate + self.broker, self._stockPositionUpdateHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.unregister(DyEventType.stockCurEntrustsUpdate + self.broker, self._stockCurEntrustsUpdateHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.unregister(DyEventType.stockCurDealsUpdate + self.broker, self._stockCurDealsUpdateHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.unregister(DyEventType.stockEntrustUpdate + self.broker, self._stockEntrustUpdateHandler, DyStockTradeEventHandType.stockCtaEngine)
        self._eventEngine.unregister(DyEventType.stockPosSyncFromBroker + self.broker, self._stockPosSyncFromBrokerHandler, DyStockTradeEventHandType.stockCtaEngine)

    @property
    def curPos(self):
        return self._curPos

    @property
    def curCash(self):
        return self._curCash

    def newCurEntrustCount(self):
        """
            生成系统唯一个委托计数器
        """
        self._curEntrustCount += 1

        return datetime.now().strftime("%H:%M:%S.%f") + str(self._curEntrustCount)

    def newCurDealCount(self):
        """
            生成系统唯一个成交计数器
        """
        self._curDealCount += 1

        return datetime.now().strftime("%H:%M:%S.%f") + str(self._curDealCount)

    def _curInit(self, tDay=None):
        """ 当日初始化 """
        self._curCash = 0 # 默认0，账户启动比策略慢，要考虑交易时间启动策略时的同步问题
        self._curPos = {} # 当前持仓, {code: DyStockPos}
        self._curTDay = tDay

        self._riskGuardCount = 0

        self._curEntrustCount = 0 # 当日委托计数
        self._curDealCount = 0 # 当日成交计数

        self._curEntrusts = {} # 当日委托, {code: [DyStockEntrust]}
        self._curDeals = OrderedDict() # 当日成交, [brokerDealId: DyStockDeal], 成交类型只有'买入'和'卖出', 类似撤单成交不考虑。也就是说考虑真正有交易的成交

        self._curWorkingCancelEntrusts = [] # 当日要撤销的委托，由于券商获取委托号的异步性导致

        self._curPosSyncData = None # 当日持仓同步数据，None表示还没有收到券商接口的持仓同步事件。
                                    # {code: {'adjFactor': x, 'cost': x}}, 'adjFactor' is 持仓复权因子。

    def onOpen(self, date):
        self._curInit(date)

        # read saved information for market daily closed
        self._load()

        self._filter = DyStockMarketFilter(list(self._curPos))

    def onTicks(self, ticks):
        ticks = self._filter.filter(ticks)

        for code, tick in ticks.items():
            pos = self._curPos.get(code)
            if pos:
                pos.onTick(tick)

    def onBars(self, bars):
        bars = self._filter.filter(bars)

        for code, bar in bars.items():
            pos = self._curPos.get(code)
            if pos:
                pos.onBar(bar)

    def _getPosSavedData(self):
        """
            获取账户持仓收盘要保存的数据
            @return: dict
        """
        posSavedData = {}
        for code, pos in self._curPos.items():
            posSavedData[code] = pos.getSavedData()

        return posSavedData

    def _restorePosSavedData(self, savedData):
        """
            恢复从磁盘保存的持仓数据
        """
        positions = savedData.get('pos')
        if positions is None:
            return

        for code, pos in positions.items():
            self._curPos[code] = DyStockPos.restorePos(pos)

    def _save(self):
        data = {}

        # for xrxd
        data['pos'] = self._getPosSavedData()

        # for chart
        data['capital'] = self.getCurCapital()
        data['cash'] = self._curCash
        data['deal'] = self._getCurDealsSavedData() # to JSON format

        # for risk control
        data['riskGuardCount'] = self._riskGuardCount

        # create directory if not existing
        path = DyCommon.createPath('Stock/Program/AccountManager/{}'.format(self.brokerName))

        # write
        fileName = os.path.join(path, '{0}.json'.format(self._curTDay))
        with open(fileName, 'w') as f:
            f.write(json.dumps(data, indent=4))

    def _getCurDealsSavedData(self):
        data = []
        for _, deal in self._curDeals.items():
            dealDict = copy.copy(deal.__dict__)
            dealDict['datetime'] = deal.datetime if isinstance(deal.datetime, str) else deal.datetime.strftime("%Y-%m-%d")
            dealDict['strategyCls'] = deal.strategyCls.chName

            del dealDict['signalInfo']
            del dealDict['minPnlRatio']
            del dealDict['tradeCost']

            data.append(dealDict)

        return data

    def _load(self):
        path = DyCommon.createPath('Stock/Program/AccountManager/{}'.format(self.brokerName))

        data = {}
        try:
            # get latest saved file
            for _, _, files in os.walk(path):
                break

            files = sorted(files)
            fileName = os.path.join(path, files[-1])

            # read
            with open(fileName) as f:
                data = json.load(f)

        except Exception:
            pass

        self._riskGuardCount = data.get('riskGuardCount', 0)

        # restore positions
        self._restorePosSavedData(data)

    def onClose(self):
        # update positions
        codes = []
        for code, pos in self._curPos.items():
            pos.onClose()

            if pos.totalVolume == 0:
                codes.append(code)

        for code in codes:
            del self._curPos[code]

        # save to disk
        self._save()

    def _newEntrust(self, type, datetime, strategyCls, code, name, price, volume):
        """
            生成新的委托，并向交易接口发送委托事件
        """
        # check if there's same code and type of entrust not done for different strategy
        entrusts = self._curEntrusts.get(code)
        if entrusts is not None:
            for entrust in entrusts:
                if (not entrust.isDone()) and entrust.type == type and entrust.strategyCls != strategyCls:
                    self._info.print('{}: 策略[{}]委托失败({}, {}, {}, 价格={}, 数量={}): 策略[{}]有未完成的委托'.format(self.__class__.__name__, strategyCls.chName,
                                                                                                   code, name, type, price, volume,
                                                                                                   entrust.strategyCls.chName), DyLogData.warning)
                                                                                                               
                    return None

        # create a new entrust
        curEntrustCount = self.newCurEntrustCount()

        entrust = DyStockEntrust(datetime, type, code, name, price, volume)
        entrust.dyEntrustId = '{0}.{1}_{2}'.format(self.broker, self._curTDay, curEntrustCount)
        entrust.strategyCls = strategyCls

        # add into 当日委托
        self._curEntrusts.setdefault(code, [])
        self._curEntrusts[code].append(copy.copy(entrust))

        # put buy/sell event
        eventType = DyEventType.stockBuy if type == DyStockOpType.buy else DyEventType.stockSell
        event = DyEvent(eventType + self.broker)
        event.data = copy.copy(entrust)

        self._eventEngine.put(event)

        return entrust

    def _newDeal(self, brokerDealId, type, datetime, strategyCls, code, name, price, volume):
        """
            生成新成交单
        """
        # create a new deal
        curDealCount = self.newCurDealCount()

        deal = DyStockDeal(datetime, type, code, name, price, volume)
        deal.dyDealId = '{}.{}_{}'.format(self.broker, self._curTDay, curDealCount)
        deal.strategyCls = strategyCls
        deal.brokerDealId = brokerDealId

        # add into deal dict
        self._curDeals[brokerDealId] = deal

        return deal

    def buy(self, datetime, strategyCls, code, name, price, volume, signalInfo=None):
        if volume < 100:
            return None # 至少买一手

        tradeCost = DyStockTradeCommon.getTradeCost(code, DyStockOpType.buy, price, volume)

        cash = price*volume + tradeCost
        if self._curCash < cash:
            return None

        newEntrust = self._newEntrust(DyStockOpType.buy, datetime, strategyCls, code, name, price, volume)
        if newEntrust is None:
            return None

        # 锁定资金
        self._curCash -= cash

        # update positions
        # 假设交易成功，以防止策略在一个执行周期内连续买入。这个由策略自己控制。
        if code in self._curPos:
            self._curPos[code].addPos(datetime, strategyCls, price, volume, tradeCost)
        else:
            self._curPos[code] = DyStockPos(datetime, strategyCls, code, name, price, volume, tradeCost)

        return newEntrust

    def sell(self, datetime, strategyCls, code, price, volume, sellReason=None, signalInfo=None):
        pos = self._curPos.get(code)
        if pos is None:
            return None

        if not pos.availVolume >= volume > 0:
            return None

        newEntrust = self._newEntrust(DyStockOpType.sell, datetime, strategyCls, code, pos.name, price, volume)
        if newEntrust is None:
            return None

        # 只减少可用数量，以防止策略在一个执行周期内连续卖出
        pos.availVolume -= volume

        return newEntrust

    def closePos(self, datetime, code, price, sellReason, signalInfo=None):
        """
            账户持仓清仓
        """
        pos = self._curPos.get(code)
        if pos is None:
            return None

        return self.sell(datetime, pos.strategyCls, code, price, pos.availVolume, sellReason, signalInfo)

    def cancel(self, cancelEntrust):
        """
            取消委托
        """
        # find corresponding entrust
        entrusts = self._curEntrusts.get(cancelEntrust.code)
        if entrusts is None:
            return False

        for entrust in entrusts:
            if entrust.dyEntrustId == cancelEntrust.dyEntrustId:
                break
        else:
            return False

        if entrust.isDone():
            self._info.print('{}: 撤销委托失败: {}'.format(self.__class__.__name__, entrust.__dict__, DyLogData.warning))
            return False

        if entrust.brokerEntrustId is None:
            self._curWorkingCancelEntrusts.append(entrust)
            return True

        # put cancel event
        event = DyEvent(DyEventType.stockCancel + self.broker)
        event.data = copy.copy(entrust)

        self._eventEngine.put(event)

        return True

    def getCurPosMarketValue(self):
        """
            get market value of all positions
        """
        value = 0
        for _, pos in self._curPos.items():
            value += pos.totalVolume * pos.price

        return value

    def getCurCodePosMarketValue(self, code):
        """
            get market value of position of sepcified code
        """
        value = None
        if code in self._curPos:
            pos = self._curPos[code]
            value = pos.totalVolume * pos.price

        return value

    def getCurCapital(self):
        """
            获取当前账户总资产
        """
        return self._curCash + self.getCurPosMarketValue()

    def getCurCodePosAvail(self, code):
        """
            获取当前股票持仓可用数量
        """
        return self._curPos[code].availVolume if code in self._curPos else 0

    def getCurCodePosCost(self, code):
        """
            获取当前股票持仓成本
        """
        return self._curPos[code].cost if code in self._curPos else None

    def _putStockMarketMonitorEvent(self):
        """
            向股票市场发送监控持仓的股票
            Note: !!!实盘跟回测有不同之处，实盘没有实现@onMonitor接口。回测时，@onMonitor是由CTA Engine调用。实盘则根据券商的持仓信息来监控持仓股票实时信息。
        """
        if self._curPos:
            event = DyEvent(DyEventType.stockMarketMonitor)
            event.data = list(self._curPos)

            self._eventEngine.put(event)

        # 新的持仓Filter
        self._filter = DyStockMarketFilter(list(self._curPos))

    def _putDealsEvent(self, deals):
        """
            @deals: [deal object]
        """
        # 向引擎推送成交回报
        if deals:
            event = DyEvent(DyEventType.stockOnDeal)
            event.data = deals

            self._eventEngine.put(event)

    def exit(self):
        self._unregisterEvent()

    def syncStrategyPos(self, strategy):
        """
            主动同步策略持仓，启动策略时由引擎调用
        """
        assert strategy.broker == self.broker

        if self._curPosSyncData is None:
            return

        strategy.syncPos(self._curPosSyncData)

    def curWorkingCancelEntrustsWrapper(func):
        """
            当前要撤销委托的装饰器。
            由于券商接口异步性，有可能策略撤销委托的时候，此委托还没有匹配好券商的委托号。
            这样在每次券商委托更新的时候，执行一次委托撤销
        """
        def wrapper(self, *args, **kwargs):
            func(self, *args, **kwargs)

            # 撤销委托
            cancelEntrusts = []
            for entrust in self._curWorkingCancelEntrusts:
                if entrust.brokerEntrustId is not None:
                    self.cancel(entrust)
                    cancelEntrusts.append(entrust)

                else:
                    if entrust.isDone(): # 网络错误可能会导致委托失败，这个时候是废单但没有券商的委托号
                        cancelEntrusts.append(entrust)

            # remove from list of current working cancel entrusts
            for entrust in cancelEntrusts:
                self._curWorkingCancelEntrusts.remove(entrust)

        return wrapper

    @curWorkingCancelEntrustsWrapper
    def _stockEntrustUpdateHandler(self, event):
        updatedEntrust = event.data

        entrusts = self._curEntrusts.get(updatedEntrust.code)
        if entrusts is None:
            return

        for entrust in entrusts:
            if entrust.dyEntrustId != updatedEntrust.dyEntrustId:
                continue

            if entrust.status == updatedEntrust.status:
                break

            entrust.status = updatedEntrust.status

            event = DyEvent(DyEventType.stockOnEntrust)
            event.data = [copy.copy(entrust)]

            self._eventEngine.put(event)
            break

    def _stockCapitalUpdateHandler(self, event):
        """
            收到来自券商接口的账户资产更新事件
        """
        header = event.data['header']
        rows = event.data['rows']

        balance = rows[0]

        self._curCash = float(balance[header.index(self.headerNameMap['capital']['availCash'])])

    def _stockPositionUpdateHandler(self, event):
        """
            收到来自券商接口的账户持仓更新事件
        """
        # unpack
        header = event.data['header']
        rows = event.data['rows']

        # 先前持仓代码
        codes = list(self._curPos)

        for data in rows:
            # unpack from 券商接口持仓数据
            code = DyStockCommon.getDyStockCode(data[header.index(self.headerNameMap['position']['code'])])
            name = data[header.index(self.headerNameMap['position']['name'])]

            totalVolume = float(data[header.index(self.headerNameMap['position']['totalVolume'])])
            availVolume = float(data[header.index(self.headerNameMap['position']['availVolume'])])

            price = float(data[header.index(self.headerNameMap['position']['price'])])
            cost = float(data[header.index(self.headerNameMap['position']['cost'])])

            # get position
            if code in self._curPos:
                pos = self._curPos[code]
                codes.remove(code)
            else:
                # new pos, we just take time now without accuracy
                if totalVolume > 0:
                    pos = DyStockPos(datetime.now(), None, code, name, price, totalVolume, 0)
                    pos.sync = True
                else:
                    continue

            # syn with positions from broker
            pos.price = price
            pos.cost = cost

            pos.totalVolume = totalVolume
            pos.availVolume = availVolume

            # write back
            self._curPos[code] = pos

        # 删除不在券商接口数据里的持仓
        for code in codes:
            del self._curPos[code]

        # 发送行情监控事件
        self._putStockMarketMonitorEvent()

        # 发送券商账户股票持仓更新事件
        event = DyEvent(DyEventType.stockOnPos)
        event.data['broker'] = self.broker
        event.data['pos'] = copy.deepcopy(self._curPos)

        self._eventEngine.put(event)

    def _convertEntrustStatus(self, status):
        """ 把券商的委托状态转换成DevilYuan委托的状态 """

        if status == '部成':
            return DyStockEntrust.Status.partDealed
        elif status == '已成':
            return DyStockEntrust.Status.allDealed
        elif status == '废单':
            return DyStockEntrust.Status.discarded
        elif status == '已撤' or status == '部撤':
            return DyStockEntrust.Status.cancelled
        else:
            return DyStockEntrust.Status.notDealed

    def _getEntrustByBrokerId(self, entrusts, brokerEntrustId):
        for entrust in entrusts:
            if entrust.brokerEntrustId == brokerEntrustId:
                return entrust

        return None

    def _getEntrust(self, code, type, price, totalVolume, brokerEntrustId):
        """
            根据key值匹配券商的委托
        """
        entrusts = self._curEntrusts.get(code)
        if entrusts is None: # 不是通过策略发出的委托
            return None

        # 优先根据券商委托号匹配
        entrust = self._getEntrustByBrokerId(entrusts, brokerEntrustId)
        if entrust is not None:
            return entrust

        # 通过委托价格，委托数量，委托类型，优先匹配最近的
        for entrust in entrusts[::-1]:
            if entrust.brokerEntrustId is not None: # 已经匹配过了
                continue

            if type == entrust.type and totalVolume == entrust.totalVolume and price == entrust.price:
                return entrust

        return None

    def _updateEntrust(self, entrust, dealedVolume, status, brokerEntrustId):
        """
            根据券商的委托，更新DevilYuan系统里的委托
            从券商的当日委托看，委托状态有变化或者是从券商首次获取对应的委托
            @return: update or not
        """
        if entrust.isDone():
            return False

        isUpdated = False

        # 有成交
        if dealedVolume > entrust.dealedVolume:
            # change dealed volume
            entrust.dealedVolume = dealedVolume

            isUpdated = True

        # 更改委托状态
        status = self._convertEntrustStatus(status)
        if status != entrust.status:
            entrust.status = status

            isUpdated = True

        # 券商委托号
        if entrust.brokerEntrustId is None:
            entrust.brokerEntrustId = brokerEntrustId

            isUpdated = True
        
        return isUpdated

    @curWorkingCancelEntrustsWrapper
    def _stockCurEntrustsUpdateHandler(self, event):
        """
            收到来自券商接口的当日委托更新事件
        """
        # unpack
        header = event.data['header']
        rows = event.data['rows']

        updatedEntrusts = []
        for data in rows[::-1]: # 从券商最近的委托开始匹配
            # unpack from 券商接口当日委托
            code = DyStockCommon.getDyStockCode(data[header.index(self.headerNameMap['curEntrust']['code'])])

            price = float(data[header.index(self.headerNameMap['curEntrust']['price'])])
            totalVolume = float(data[header.index(self.headerNameMap['curEntrust']['totalVolume'])])
            dealedVolume = float(data[header.index(self.headerNameMap['curEntrust']['dealedVolume'])])

            type = data[header.index(self.headerNameMap['curEntrust']['type'])]
            status = data[header.index(self.headerNameMap['curEntrust']['status'])]
            brokerEntrustId = data[header.index(self.headerNameMap['curEntrust']['entrustId'])]

            # get matched entrust from saved DevilYuan entrusts
            entrust = self._getEntrust(code, type, price, totalVolume, brokerEntrustId)
            if entrust is None: # 不是通过策略发出的委托
                continue

            # update entrust
            if self._updateEntrust(entrust, dealedVolume, status, brokerEntrustId):
                updatedEntrusts.append(copy.copy(entrust))

        # 向引擎推送委托回报事件
        if updatedEntrusts:
            event = DyEvent(DyEventType.stockOnEntrust)
            event.data = updatedEntrusts

            self._eventEngine.put(event)

    def _matchDyEntrustByBrokerDeal(self, dyEntrust, dealType, dealedVolume, brokerEntrustId=None):
        """
            根据券商的成交单匹配DevilYuan系统的委托单。
            !!!这里只匹配有成交的委托单，也就是说发生金钱交易，撤单成交则不考虑。
            子类可以重载此函数
        """
        # 由于券商的当日委托推送和当日成交推送是异步的，所以要考虑这之间可能有新的委托
        # 这里不考虑废单撤单状态，整个时序保证了不可能
        # !!!如果有跟策略股票和类型相同的手工委托单（通过其他系统的委托），则可能出现会错误地认为是由策略发出的。
        if dyEntrust.status != DyStockEntrust.Status.allDealed and dyEntrust.status != DyStockEntrust.Status.partDealed:
            return False

        if brokerEntrustId is not None:
            if dyEntrust.brokerEntrustId != brokerEntrustId:
                return False

            return True

        if dealType != dyEntrust.type:
            return False

        # 在获取当日成交的时候，同一个委托又有了新的成交。
        # 由于推送的委托是上一次的，并且是贪婪式匹配，如果同一时刻两个策略发出相同的委托，则可能匹配错。
        # 但由于策略生成新委托时，若同一类型的委托还没有完成，账户管理类则拒绝策略的新委托。
        # 这个保证了匹配错误不会发生。
        if dyEntrust.matchedDealedVolume + dealedVolume > dyEntrust.dealedVolume:
            return False

        return True

    def _stockCurDealsUpdateHandler(self, event):
        """
            收到来自券商接口的当日成交更新事件
            不考虑撤单成交
            若撤单并且撤单成功，则券商的成交单交易类型是'撤单成交'，成交价和成交数跟委托一样，但成交额是0
        """
        # unpack
        header = event.data['header']
        rows = event.data['rows']

        newDeals = []
        for data in rows:
            # unpack from 券商接口当日成交
            code = DyStockCommon.getDyStockCode(data[header.index(self.headerNameMap['curDeal']['code'])])

            price = float(data[header.index(self.headerNameMap['curDeal']['price'])])
            dealedVolume = float(data[header.index(self.headerNameMap['curDeal']['dealedVolume'])])
            datetime = data[header.index(self.headerNameMap['curDeal']['datetime'])]
            type = data[header.index(self.headerNameMap['curDeal']['type'])]
            brokerDealId = data[header.index(self.headerNameMap['curDeal']['dealId'])]

            # 不是每个券商的成交单里有对应的委托编号
            try:
                brokerEntrustId = data[header.index(self.headerNameMap['curDeal']['entrustId'])]
            except:
                brokerEntrustId = None

            # 已经匹配过了
            if brokerDealId in self._curDeals:
                continue

            # compare with saved DevilYuan entrusts
            entrusts = self._curEntrusts.get(code)
            if entrusts is None: # 不是通过策略发出的委托
                continue

            # 从最近的时间开始遍历
            for entrust in entrusts[::-1]:
                if not self._matchDyEntrustByBrokerDeal(entrust, type, dealedVolume, brokerEntrustId):
                    continue

                entrust.matchedDealedVolume += dealedVolume

                # create a new deal
                deal = self._newDeal(brokerDealId, entrust.type, datetime, entrust.strategyCls, entrust.code, entrust.name, price, dealedVolume)
                newDeals.append(deal)
                break

        # 向引擎推送成交回报
        self._putDealsEvent(newDeals)

    def _stockPosSyncFromBrokerHandler(self, event):
        """
            收到来自券商接口的持仓同步事件
            !!!如果交易不是通过策略，或者持仓同步不是在开盘时，可能会导致信息不一致或者错误。
        """
        # unpack
        header = event.data['header']
        rows = event.data['rows']

        # it's synchronized from broker
        self._curPosSyncData = {}

        for data in rows:
            # unpack from 券商接口持仓数据
            code = DyStockCommon.getDyStockCode(data[header.index(self.headerNameMap['position']['code'])])
            name = data[header.index(self.headerNameMap['position']['name'])]

            totalVolume = float(data[header.index(self.headerNameMap['position']['totalVolume'])])
            availVolume = float(data[header.index(self.headerNameMap['position']['availVolume'])])

            price = float(data[header.index(self.headerNameMap['position']['price'])])
            cost = float(data[header.index(self.headerNameMap['position']['cost'])])

            # get position
            pos = self._curPos.get(code)
            if pos is None:
                continue

            # set sync data firstly
            self._curPosSyncData[code] = {'volumeAdjFactor': totalVolume/pos.totalVolume,
                                          'priceAdjFactor': pos.cost/cost,
                                          'cost': cost
                                          }

            # syn with positions from broker
            pos.price = price
            pos.cost = cost

            pos.totalVolume = totalVolume
            pos.availVolume = availVolume

            pos.priceAdjFactor = self._curPosSyncData[code]['priceAdjFactor']
            pos.volumeAdjFactor = self._curPosSyncData[code]['volumeAdjFactor']

            if pos.priceAdjFactor != 1:
                pos.xrd = True

            pos.sync = True

        # 发送行情监控事件
        self._putStockMarketMonitorEvent()

        # 发送股票持仓同步事件
        event = DyEvent(DyEventType.stockPosSyncFromAccountManager)
        event.data['broker'] = self.broker
        event.data['data'] = self._curPosSyncData

        self._eventEngine.put(event)

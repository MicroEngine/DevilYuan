import copy
from datetime import *

from DyCommon.DyCommon import *
from ..DyStockBackTestingCommon import *
from ...Trade.DyStockTradeCommon import *
from ...Trade.AccountManager.DyStockPos import *
from ...Trade.AccountManager.StopMode.DyStockStopLossMaMode import *
from ...Trade.AccountManager.StopMode.DyStockStopProfitMaMode import *
from ...Trade.AccountManager.StopMode.DyStockStopLossPnlRatioMode import *
from ...Trade.AccountManager.StopMode.DyStockStopLossStepMode import *
from ...Trade.AccountManager.StopMode.DyStockStopProfitPnlRatioMode import *
from ...Trade.AccountManager.StopMode.DyStockStopTimeMode import *


class DyStockBackTestingAccountManager:
    """
        回测账户管理
        模拟实盘账户管理，接口跟实盘账户类保持一致
        实盘账户管理不含有停损模块和风控模块，这里只是为回测时参数寻优提供便利，所以提供了通用性的停损模块和风控模块。
        策略实盘时要实现自己的停损和风控模块。
    """
    broker = 'BackTesting'


    def __init__(self, eventEngine, info, dataEngine, settings):
        self._eventEngine = eventEngine
        self._info = info

        self._dataEngine = dataEngine
        self._daysEngine = self._dataEngine.daysEngine # for easy access

        # settings
        self._initCash = settings['cash']
        self._curCash = settings['cash']

        self._initStopMode(settings['stopSettings'])

        # 回测参数组合和周期
        self._paramGroupNo = None
        self._period = None

        # 跟交易相关的账户持久数据
        self._curPos = {} # 当前持仓, {code: DyStockPos}
        self._deals = [] # 历史成交

        # 风控
        self._riskGuardNbr = settings['riskGuard']
        self._riskGuardCount = 0 # 一旦发生某些原因(清仓)的closePos，则进行风控，也就是说@self._riskGuardNbr个交易日内禁止买入

        # 当日初始化
        self._curInit()

        # reset to T+1
        DyStockTradeCommon.T1 = True

    def _initStopMode(self, stopSettings):
        # default
        self._stopTimeMode = DyStockStopMode(self)
        self._stopLossMode = DyStockStopMode(self)
        self._stopProfitMode = DyStockStopMode(self)

        if 'stopLoss' in stopSettings:
            name, param = stopSettings['stopLoss']
            if name == '固定':
                self._stopLossMode = DyStockStopLossPnlRatioMode(self, *param)
            elif name == '均线':
                self._stopLossMode = DyStockStopLossMaMode(self, self._dataEngine, *param)
            elif name == '阶梯':
                self._stopLossMode = DyStockStopLossStepMode(self, *param)

        if 'stopProfit' in stopSettings:
            name, param = stopSettings['stopProfit']
            if name == '固定':
                self._stopProfitMode = DyStockStopProfitPnlRatioMode(self, *param)
            elif name == '均线':
                self._stopProfitMode = DyStockStopProfitMaMode(self, self._dataEngine, *param)

        if 'stopTime' in stopSettings:
            name, param = stopSettings['stopTime']
            if name == '固定':
                self._stopTimeMode = DyStockStopTimeMode(self, *param)

    @property
    def curPos(self):
        return self._curPos

    @property
    def curCash(self):
        return self._curCash

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
        # 由于买入委托锁定了资金，所以需要处理未成交的买入委托
        entrustCash = 0
        for entrust in self._curNotDoneEntrusts:
            type = entrust.type
            code = entrust.code
            price = entrust.price
            volume = entrust.totalVolume

            if type == DyStockOpType.buy:
                tradeCost = DyStockTradeCommon.getTradeCost(code, type, price, volume)
                entrustCash += price*volume + tradeCost

        return self._curCash + self.getCurPosMarketValue() + entrustCash

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

    def _processDealedEntrusts(self, dealedEntrusts, ticks):
        """
            处理成交的委托
        """
        for entrust in dealedEntrusts:
            # update
            entrust.status = DyStockEntrust.Status.allDealed
            entrust.dealedVolume = entrust.totalVolume
            self.matchedDealedVolume = entrust.totalVolume

            type = entrust.type
            code = entrust.code
            name = entrust.name
            price = entrust.price
            volume = entrust.totalVolume
            strategyCls = entrust.strategyCls
            signalInfo = entrust.signalInfo
            entrustDatetime = entrust.entrustDatetime

            datetime = ticks.get(code).datetime
            tradeCost = DyStockTradeCommon.getTradeCost(code, type, price, volume)

            # remove from not done entrusts list
            self._curNotDoneEntrusts.remove(entrust)

            # add into 等待推送的当日委托list
            self._curWaitingPushEntrusts.append(entrust)

            # new deal
            self._curDealCount += 1
            deal = DyStockDeal(datetime, type, code, name, price, volume, tradeCost, signalInfo=signalInfo, entrustDatetime=entrustDatetime)
            deal.dyDealId = '{}.{}_{}'.format(self.broker, self._curTDay, self._curDealCount)

            self._curDeals.append(deal)
            self._deals.append(deal)
            self._curWaitingPushDeals.append(deal)

            # update positions
            if type == DyStockOpType.buy: # 买入
                if code in self._curPos:
                    pos = self._curPos[code]
                    pos.addPos(datetime, strategyCls, price, volume, tradeCost)
                else:
                    self._curPos[code] = DyStockPos(datetime, strategyCls, code, name, price, volume, tradeCost)

            else: # 卖出
                pos = self._curPos[code]

                pnl, pnlRatio = pos.removePos(price, volume, tradeCost, removeAvailVolume=False)
                assert pnl is not None

                deal.pnl = pnl
                deal.pnlRatio = pnlRatio
                deal.holdingPeriod = pos.holdingPeriod
                deal.xrd = pos.xrd
                deal.minPnlRatio = pos.minPnlRatio

                cash = price*volume - tradeCost
                self._curCash += cash

    def _CrossCurNotDoneEntrustsByTicks(self, ticks):
        """
            每tick撮合当日未成交的委托
            为了简单，这里没有考虑成交量，当然可以考虑成交量做更精细化的成交处理。
        """
        # 撮合委托
        dealedEntrusts = []
        for entrust in self._curNotDoneEntrusts:
            tick = ticks.get(entrust.code)
            if tick is None:
                continue

            if entrust.type == DyStockOpType.buy:
                if tick.price >= entrust.price:
                    continue
            else:
                if tick.price <= entrust.price:
                    continue

            dealedEntrusts.append(entrust)

        # 处理成交的委托
        self._processDealedEntrusts(dealedEntrusts, ticks)

    def _isBarLimitDown(self, bar):
        return bar.low == bar.high and (bar.low - bar.preClose)/bar.preClose*100 <= DyStockCommon.limitDownPct

    def _isBarLimitUp(self, bar):
        return bar.low == bar.high and (bar.high - bar.preClose)/bar.preClose*100 >= DyStockCommon.limitUpPct

    def _CrossCurNotDoneEntrustsByBars(self, bars):
        """
            每Bar撮合当日未成交的委托
            @bars: {code: bar}
        """
        # 撮合委托
        dealedEntrusts = []
        for entrust in self._curNotDoneEntrusts:
            bar = bars.get(entrust.code)
            if bar is None:
                continue

            if bar.mode[-1] == 'd': # 日线回测，直接撮合，2017.11.09
                if entrust.type == DyStockOpType.buy:
                    if (bar.close - bar.preClose)/bar.preClose*100 < DyStockCommon.limitUpPct: # 涨停则不买入
                        dealedEntrusts.append(entrust)
                else:
                    if (bar.close - bar.preClose)/bar.preClose*100 > DyStockCommon.limitDownPct: # 跌停则不卖出
                        dealedEntrusts.append(entrust)

            else: # 分钟回测，穿价撮合
                if entrust.type == DyStockOpType.buy:
                    if bar.low < entrust.price or (bar.low == entrust.price and self._isBarLimitDown(bar)): # 穿价或者跌停买入
                        dealedEntrusts.append(entrust)
                else:
                    if bar.high > entrust.price or (bar.high == entrust.price and self._isBarLimitUp(bar)): # 穿价或者涨停卖出
                        dealedEntrusts.append(entrust)

        # 处理成交的委托
        self._processDealedEntrusts(dealedEntrusts, bars)

    def _newEntrust(self, type, datetime, strategyCls, code, name, price, volume, signalInfo=None, tickOrBar=None):
        """
            生成新的委托
        """
        # create a new entrust
        self._curEntrustCount += 1

        entrust = DyStockEntrust(datetime, type, code, name, price, volume)
        entrust.dyEntrustId = '{}.{}_{}'.format(self.broker, self._curTDay, self._curEntrustCount)
        entrust.strategyCls = strategyCls
        entrust.status = DyStockEntrust.Status.notDealed
        entrust.signalInfo = signalInfo

        self._curWaitingPushEntrusts.append(entrust) # add into 等待推送的当日委托list
        self._curNotDoneEntrusts.append(entrust) # add into 未成交委托list

        # 日线回测，则直接撮合
        if strategyCls.backTestingMode == 'bar1d':
            self._CrossCurNotDoneEntrustsByBars({tickOrBar.code: tickOrBar})

        return entrust

    def buy(self, datetime, strategyCls, code, name, price, volume, signalInfo=None, tickOrBar=None):
        """
            @tickOrBar: 主要为了日内回测
        """
        if volume < 100:
            return None # 至少买一手

        if self._riskGuardCount > 0:
            return None # 风控中

        tradeCost = DyStockTradeCommon.getTradeCost(code, DyStockOpType.buy, price, volume)

        cash = price*volume + tradeCost
        if self._curCash < cash:
            return None

        self._curCash -= cash

        # 生成新的委托
        return self._newEntrust(DyStockOpType.buy, datetime, strategyCls, code, name, price, volume, signalInfo=signalInfo, tickOrBar=tickOrBar)
    
    def sell(self, datetime, strategyCls, code, price, volume, sellReason=None, signalInfo=None, tickOrBar=None):
        """
            @tickOrBar: 主要为了日内回测
        """
        pos = self._curPos.get(code)
        if pos is None:
            return None

        name = pos.name

        if not pos.availVolume >= volume > 0:
            return None

        pos.availVolume -= volume

        # 生成新的委托
        return self._newEntrust(DyStockOpType.sell, datetime, strategyCls, code, name, price, volume, signalInfo=signalInfo, tickOrBar=tickOrBar)

    def setParamGroupNoAndPeriod(self, paramGroupNo, period):
        self._paramGroupNo = paramGroupNo
        self._period = period

    def _curInit(self, tDay=None):
        """ 当日初始化 """

        self._curTDay = tDay

        self._curDeals = [] # 当日成交

        self._curEntrustCount = 0
        self._curDealCount = 0

        # 需要推送给策略的委托和成交回报
        self._curWaitingPushDeals = []
        self._curWaitingPushEntrusts = []

        self._curNotDoneEntrusts = [] # 当日未成交委托

        # 风控
        if self._riskGuardCount > 0:
            self._riskGuardCount -= 1

    def onMonitor(self):
        return list(self._curPos)

    def onTicks(self, ticks):
        # 撮合委托
        self._CrossCurNotDoneEntrustsByTicks(ticks)

        # 先更新持仓
        for code, pos in self._curPos.items():
            tick = ticks.get(code)
            if tick is not None:
                pos.onTick(tick)

        # 止损
        self._stopLossMode.onTicks(ticks)

        # 止盈
        self._stopProfitMode.onTicks(ticks)

        # 止时
        self._stopTimeMode.onTicks(ticks)

    def onBars(self, bars):
        # 撮合委托
        self._CrossCurNotDoneEntrustsByBars(bars)

        # 先更新持仓
        for code, pos in self._curPos.items():
            bar = bars.get(code)
            if bar is not None:
                pos.onBar(bar)

        # 止损
        self._stopLossMode.onBars(bars)

        # 止盈
        self._stopProfitMode.onBars(bars)

        # 止时
        self._stopTimeMode.onBars(bars)

    def _onCloseCurNotDoneEntrusts(self):
        """
            处理收盘后的未成交委托
        """
        # 处理未成交的买入委托
        for entrust in self._curNotDoneEntrusts:
            type = entrust.type
            code = entrust.code
            name = entrust.name
            price = entrust.price
            volume = entrust.totalVolume
            datetime = entrust.entrustDatetime

            self._info.print('{}未成交委托: {}({}), {}, 价格{}, {}股, 委托时间{}'.format(self._curTDay,
                                                                             code, name, type, price, volume,
                                                                             datetime.strftime('%H:%M:%S')), DyLogData.ind1)

            if type == DyStockOpType.buy:
                tradeCost = DyStockTradeCommon.getTradeCost(code, type, price, volume)

                self._curCash += price*volume + tradeCost

    def onClose(self):
        # remove pos
        for code in list(self._curPos):
            if self._curPos[code].totalVolume == 0:
                del self._curPos[code]

        # update positions
        for _, pos in self._curPos.items():
            pos.onClose()

        # 处理收盘后的未成交委托
        self._onCloseCurNotDoneEntrusts()

    def getCurAckData(self, strategyCls):
        """ 获取当日策略回测结果数据 """

        ackData = DyStockBackTestingStrategyAckData(datetime.strptime(self._curTDay + ' 15:00:00', '%Y-%m-%d %H:%M:%S'), strategyCls, self._paramGroupNo, self._period, True)

        ackData.initCash = self._initCash
        ackData.curCash = self._curCash
        ackData.curPos = copy.deepcopy(self._curPos)
        ackData.day = self._curTDay
        ackData.deals = self._curDeals

        return ackData

    def onOpen(self, date):
        
        # 当日初始化
        self._curInit(date)

        # 初始化止损模式
        if not self._stopLossMode.onOpen(date):
            return False

        # 初始化止盈模式
        if not self._stopProfitMode.onOpen(date):
            return False

        # 初始化当前持仓
        for _, pos in self._curPos.items():
            if not pos.onOpen(date, self._dataEngine):
                return False

        return True

    def closePos(self, datetime, code, price, sellReason, signalInfo=None, tickOrBar=None):
        entrust = None
        if code in self._curPos:
            pos = self._curPos[code]

            entrust = self.sell(datetime, pos.strategyCls, code, price, pos.availVolume, sellReason, signalInfo, tickOrBar)

        # 风控, 不管有没有持仓
        if sellReason == DyStockSellReason.liquidate:
            if self._riskGuardNbr > 0: # 风控 is on
                self._riskGuardCount = self._riskGuardNbr + 1

        return entrust

    def popCurWaitingPushDeals(self):
        deals = self._curWaitingPushDeals

        self._curWaitingPushDeals = []

        return deals

    def popCurWaitingPushEntrusts(self):
        entrusts = self._curWaitingPushEntrusts

        self._curWaitingPushEntrusts = []

        return entrusts

    def syncStrategyPos(self, strategy):
        """
            由于除复权的问题，同步策略的持仓。
            每次账户Tick或者Bar回测完后调用，一定要先于策略的onTicks或者onBars。
        """
        # 构造持仓同步数据
        syncData = {}
        for code, pos in self._curPos.items():
            if pos.sync: # 只跟策略同步同步过的持仓。若持仓当日停牌或者前面tick数据缺失，则持仓不会被同步。所以也不能假设停牌，而把复权因子设为1。
                syncData[code] = {'priceAdjFactor': pos.priceAdjFactor,
                                  'volumeAdjFactor': pos.volumeAdjFactor,
                                  'cost': pos.cost
                                  }
        # 同步策略持仓
        strategy.syncPos(syncData)
        
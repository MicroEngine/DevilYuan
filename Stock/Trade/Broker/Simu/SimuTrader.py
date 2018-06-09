import os
import json
from time import sleep
from datetime import datetime

from EventEngine.DyEvent import *
from ..WebTrader import *
from ...DyStockTradeCommon import *
from ....Data.Engine.DyStockDataDaysEngine import *
from ....Data.Engine.DyStockMongoDbEngine import *


class SimuTrader(WebTrader):
    """
        模拟券商Web接口，参照的是国泰君安
        !!!一定保证账户数据的保存的连续性
    """
    brokerName = '模拟'
    broker = 'simu'

    heartBeatTimer = 60*10

    dealHeader = ['证券名称', '证券代码', '合同号', '交易类型', '成交价', '成交数', '成交额', '成交时间']
    entrustHeader = ['委托序号', '证券代码', '证券名称', '类型', '委托价格', '委托数量', '委托时间', '成交数量', '委托状态']
    balanceHeader = ['可用余额', '证券市值', '资产总值']
    positionHeader = ['证券代码', '证券名称', '实际数量', '可用数量', '市值(元)', '最新价格', '成本价(元)', '浮动盈亏(元)', '盈亏比(%)', '除权除息'] # 国泰君安没有'盈亏比(%)'和'除权除息'字段

    accountPath = 'Stock/Program/Broker/{0}'.format(brokerName)
    initCash = 200000


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)

    def _preLogin(self):
        self._startTime = datetime.now()

        self._curDealNo = 0
        self._curEntrustNo = 0

        # 券商账户数据仿真，table格式
        self._simuCurDeals = []
        self._simuCurEntrusts = []

        self._curNoTickCodes = set() # 当日没有Tick数据的股票代码，可能停牌

    def _postLogout(self):
        pass

    @classmethod
    def __constructErrorDaysEngine(cls, eventEngine):
        errorInfo = DyErrorInfo(eventEngine)
        mongoDbEngine = DyStockMongoDbEngine(errorInfo)

        errorDaysEngine = DyStockDataDaysEngine(eventEngine, mongoDbEngine, None, errorInfo, registerEvent=False)

        return errorDaysEngine

    @classmethod
    def __readAccountFile(cls):
        data = {}
        date = None

        try:
            # get latest account file
            path = DyCommon.createPath(cls.accountPath)
            for _, _, files in os.walk(path):
                break

            files = sorted(files)
            accountFile = os.path.join(path, files[-1])

            # read
            with open(accountFile) as f:
                data = json.load(f)

                date = files[-1][:-5]

        except:
            pass

        return date, data

    @classmethod
    def updatePosClose(cls, eventEngine, info):
        """
            更新持仓收盘价到文件
        """
        info.print('交易接口[{0}]: 开始更新持仓数据的收盘价...'.format(cls.brokerName), DyLogData.ind1)

        date, data = cls.__readAccountFile()
        if date is None:
            info.print('交易接口[{0}]: 没有持仓数据'.format(cls.brokerName))
            return True

        if data.get('posClose') is not None:
            info.print('交易接口[{0}]: 持仓数据的收盘价已经更新过了'.format(cls.brokerName))
            return True

        positions = data.get('pos')
        if positions is None:
            info.print('交易接口[{0}]: 持仓数据文件格式错误: 没有pos对应的数据'.format(cls.brokerName), DyLogData.error)
            return False

        errorDaysEngine = cls.__constructErrorDaysEngine(eventEngine)

        # load close for each position
        closeData = {}
        for pos in positions:
            code = pos[0]
            if not errorDaysEngine.loadCode(code, [date, 0], latestAdjFactorInDb=False):
                info.print('交易接口[{0}]: {1}({2})数据库数据有问题'.format(cls.brokerName, code, pos[1]), DyLogData.error)
                return False

            df = errorDaysEngine.getDataFrame(code)
            
            closeData[code] = df.ix[0, 'close']

        # save to file
        data.update({'posClose': closeData})

        accountFile = os.path.join(DyCommon.createPath(cls.accountPath), '{}.json'.format(date))
        with open(accountFile, 'w') as f:
            f.write(json.dumps(data, indent=4))

        info.print('交易接口[{0}]: 持仓数据的收盘价更新完成'.format(cls.brokerName), DyLogData.ind1)

        return True

    def __verifyAccountFileDate(self, date):
        if date is None:
            return True

        # 用户没有通过UI指定策略准备数据的日期, 即前一交易日
        if DyStockTradeCommon.strategyPreparedDataDay is None:
            if self._curDay == date:
                return True

            elif self._curDay > date: # 实盘
                
                errorDaysEngine = self.__constructErrorDaysEngine(self._eventEngine)
                dateFromDb = errorDaysEngine.tDaysOffsetInDb(DyTime.getDateStr(self._curDay, -1), 0)

                if date != dateFromDb:
                    self._info.print('交易接口[{0}]: 保存的持仓数据日期[{1}]跟数据库最近的交易日[{2}]不相同'.format(self.brokerName, date, dateFromDb), DyLogData.error)
                    return False

                return True

            else:
                self._info.print('交易接口[{0}]: 保存的持仓数据日期[{1}]晚于今日日期[{2}]'.format(self.brokerName, date, self._curDay), DyLogData.error)
                return False

        else:
            if date == DyStockTradeCommon.strategyPreparedDataDay:
                return True
            else:
                self._info.print('交易接口[{0}]: 保存的持仓数据日期[{1}]跟用户指定的日期[{2}]不相同'.format(self.brokerName, date, DyStockTradeCommon.strategyPreparedDataDay), DyLogData.error)
                return False

    def __loadAccount(self):
        """
            Read latest account data
        """
        date, data = self.__readAccountFile()

        # 验证保存数据的日期正确性
        if not self.__verifyAccountFileDate(date):
            return False

        # 收盘数据不是今天的并且还没更新过持仓的收盘价，则需要更新持仓的收盘价到文件
        if date is not None and  self._curDay != date and data.get('posClose') is None:
            self._info.print('交易接口[{0}]: 保存的持仓数据[{1}]没有收盘价'.format(self.brokerName, date), DyLogData.ind)

            # update close of pos
            if not self.updatePosClose(self._eventEngine, self._info):
                return False

            # read file again to get close of pos
            date, data = self.__readAccountFile()

        # 持久性数据
        self._balance = data.get('balance', [self.initCash, 0, self.initCash])
        self._positions = data.get('pos', [])
        self._posDate = date # 持仓保存的日期
        self._posCloses = data.get('posClose', {}) # 持仓的收盘价，为了除权除息
        self._posSync = False

        # 当日相关的数据
        if self._curDay == date:
            self._curDealNo = data.get('curDealNo', 0)
            self._curEntrustNo = data.get('curEntrustNo', 0)

            self._simuCurDeals = data.get('curDeals', [])
            self._simuCurEntrusts = data.get('curEntrusts', [])

        return True

    def __saveAccount(self, close=True):
        """
            @close: 收盘了
        """
        # update available volumes after market close
        if close:
            positions = []
            for pos in self._positions:
                pos[3] = pos[2]

                # delete empty position
                if pos[2] > 0:
                    positions.append(pos)

            self._positions = positions

        # save
        accountFile = os.path.join(DyCommon.createPath(self.accountPath), '{}.json'.format(self._curDay))
        with open(accountFile, 'w') as f:
            data = {'balance': self._balance,
                    'pos': self._positions,
                    'curDealNo': self._curDealNo,
                    'curEntrustNo': self._curEntrustNo,
                    'curDeals': self._simuCurDeals,
                    'curEntrusts': self._simuCurEntrusts
                    }

            f.write(json.dumps(data, indent=4))

    def _login(self):
        """
            登录到券商的Web页面
        """
        # 从文件载入账户数据
        if not self.__loadAccount():
            return False

        self._isClosed = False # 是否收盘了

        # 向股票市场发送监控的股票池
        # 主要原因是如果交易时间启动交易系统，由于异步，股票CTA引擎如果需要实时计算准备数据，则对应的持仓没法发送给市场引擎。
        if self._positions:
            event = DyEvent(DyEventType.stockMarketMonitor)
            event.data = [pos[0] for pos in self._positions]

            self._eventEngine.put(event)

        sleep(1)
        return True

    def _compareEntrusts(self, entrusts, newEntrusts):
        """
            比较两组委托的状态
            虚函数，由基类调用
            @entrusts: old entrusts
            @newEntrusts: new entrusts
            @return: 委托状态变化，所有委托都完成
        """
        return True, True

    def getCurDeals(self):
        """
            获取当日成交
            @return: header, [[item]]
        """
        return self.dealHeader, self._simuCurDeals

    @WebTrader.retryWrapper
    def buy(self, code, name, price, volume):
        # check if have enough cash to buy
        tradeCost = DyStockTradeCommon.getTradeCost(code, DyStockOpType.buy, price, volume)
        dealAmount = tradeCost + price*volume
        availCash = self._balance[0] - dealAmount
        if availCash < 0:
            self._info.print('交易接口[{0}]: 买入[{1}: {2}], 委托价格{3}元, {4}股, 超出可用余额'.format(self.brokerName, code, name, price, volume), DyLogData.warning)
            return False
        
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # entrust
        self._curEntrustNo += 1
        entrustNo = '{0}_{1}'.format(self._curDay, self._curEntrustNo)

        self._simuCurEntrusts.append([entrustNo, code, name, '买入', price, volume, time, volume, '已成'])

        # deal
        self._curDealNo += 1
        dealNo = '{0}_{1}'.format(self._curDay, self._curDealNo)
        
        self._simuCurDeals.append([name, code, dealNo, '买入', price, volume, dealAmount - tradeCost, time])

        # position
        for pos in self._positions:
            if pos[0] == code:
                totalVolume = pos[2] + volume
                marketValue = price*totalVolume
                cost = (dealAmount + pos[6]*pos[2])/totalVolume

                # update
                pos[2] = totalVolume
                pos[3] = pos[3] if DyStockTradeCommon.T1 else totalVolume
                pos[4] = marketValue
                pos[5] = price
                pos[6] = cost
                pos[7] = (price - cost)*totalVolume
                pos[-2] = (price - pos[6])/pos[6]*100 if pos[6] > 0 else 'N/A'
                break

        else: # new position
            cost = dealAmount/volume
            self._positions.append([code, name, volume, 0 if DyStockTradeCommon.T1 else volume, price*volume, price, cost, (price - cost)*volume, (price - cost)/cost*100, '否'])

        # balance
        self._balance[0] = availCash
        self._balance[1] += price*volume
        self._balance[2] -= tradeCost

        return True

    def getCurEntrusts(self):
        """
            获取当日委托
            @return: header, [[item]]
        """
        return self.entrustHeader, self._simuCurEntrusts

    @WebTrader.retryWrapper
    def cancel(self, entrust):
        """ 撤销委托 """
        self._info.print('交易接口[{0}]: 撤销委托({1}), 券商返回错误: 委托已成交，无法撤销'.format(self.brokerName, entrust.brokerEntrustId), DyLogData.warning)
        return False

    @WebTrader.retryWrapper
    def sell(self, code, name, price, volume):
        # check if have enough volume to sell
        tradeCost = DyStockTradeCommon.getTradeCost(code, DyStockOpType.sell, price, volume)
        dealAmount = price*volume - tradeCost  # 成交额已经去除了交易费用
        availCash = self._balance[0] + dealAmount

        for posIndex, pos in enumerate(self._positions):
            if pos[0] == code:
                if pos[3] < volume:
                    self._info.print('交易接口[{0}]: 卖出[{1}: {2}], 委托价格{3}元, {4}股, 可用数量不足'.format(self.brokerName, code, name, price, volume), DyLogData.warning)
                    return False

                break
        else:
            self._info.print('交易接口[{0}]: 卖出[{1}: {2}], 委托价格{3}元, {4}股, 没有持仓'.format(self.brokerName, code, name, price, volume), DyLogData.warning)
            return False

        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # entrust
        self._curEntrustNo += 1
        entrustNo = '{0}_{1}'.format(self._curDay, self._curEntrustNo)

        self._simuCurEntrusts.append([entrustNo, code, name, '卖出', price, volume, time, volume, '已成'])

        # deal
        self._curDealNo += 1
        dealNo = '{0}_{1}'.format(self._curDay, self._curDealNo)
        
        self._simuCurDeals.append([name, code, dealNo, '卖出', price, volume, dealAmount + tradeCost, time])

        # position
        totalVolume = pos[2] - volume
        availVolume = pos[3] - volume
        marketValue = price*totalVolume
        cost = (pos[6]*pos[2] - dealAmount)/totalVolume if totalVolume > 0 else pos[6]

        # update
        pos[2] = totalVolume
        pos[3] = availVolume
        pos[4] = marketValue
        pos[5] = price
        pos[6] = cost
        pos[7] = (price - cost)*totalVolume
        pos[-2] = (price - pos[6])/pos[6]*100 if pos[6] > 0 else 'N/A'

        # balance
        self._balance[0] = availCash
        self._balance[1] -= price*volume
        self._balance[2] -= tradeCost

        return True

    @WebTrader.retryWrapper
    def _logout(self, oneKeyHangUp=False):
        if not oneKeyHangUp:
            self.__saveAccount(close=False)

        return True

    @WebTrader.retryWrapper
    def getBalance(self, parse=True, fromBroker=True):
        """
            获取账户资金状况
            @parse: 是否要解析HTML页面
            @return: header, [[item]]
        """
        return self.balanceHeader, [self._balance]

    def getPositions(self, fromBroker=True):
        """
            获取账户持仓
            @return: header, [[item]], autoForegroundColName
        """
        return self.positionHeader, self._positions, '浮动盈亏(元)'

    def _sendHeartBeat(self, event):
        """
            It's tricky that using heart beat to save account data
        """
        # 这里只是使用了时间跨越，但没有考虑日期，非交易日可能也会保存账户数据。
        #!!! 对于非交易日的持仓数据文件，请务必自己手动清除。
        if datetime.now().strftime("%H:%M:%S") > '15:05:00' and self._startTime.strftime("%H:%M:%S") < '15:00:00':
            if self._isClosed:
                return

            self._info.print('交易接口[{}]: 保存账户当日收盘数据'.format(self.brokerName), DyLogData.ind1)

            self._isClosed = True
            self.__saveAccount(close=True)

    def __updatePerTicks(self, ticks):
        """
            每Ticks更新
        """
        # positions
        marketValue = 0
        for pos in self._positions:
            tick = ticks.get(pos[0])
            if tick is None:
                if pos[0] not in self._curNoTickCodes:
                    self._curNoTickCodes.add(pos[0])
                    self._info.print('交易接口[{0}]: 无法获取{1}({2})的Tick数据，可能停牌'.format(self.brokerName, pos[0], pos[1]), DyLogData.warning)

                marketValue += pos[4]
                continue

            if pos[0] in self._curNoTickCodes:
                self._curNoTickCodes.remove(pos[0])
                self._info.print('交易接口[{0}]: 获取{1}({2})的Tick数据成功'.format(self.brokerName, pos[0], pos[1]), DyLogData.ind)

            pos[4] = tick.price*pos[2]
            pos[5] = tick.price
            pos[7] = (tick.price - pos[6])*pos[2]
            pos[-2] = (tick.price - pos[6])/pos[6]*100 if pos[6] > 0 else 'N/A'

            marketValue += pos[4]

        # balance
        self._balance[1] = marketValue
        self._balance[2] = self._balance[0] + marketValue

    def __syncPos(self, ticks):
        # 已经同步过持仓了
        if self._posSync:
            return

        if DyStockTradeCommon.enableCtaEngineTickOptimization:
            # 确保实时tick的日期比持仓要新
            tick = ticks.get(DyStockCommon.szIndex)
            if tick is None:
                return

            if tick.date <= self._posDate:
                return

            # 确保现在是有效交易时间
            if not '09:25:00' <= tick.time < '15:00:00':
                return

        # 更新持仓
        for pos in self._positions:
            tick = ticks.get(pos[0])
            if tick is None: # 由于login的时候的sleep，所以时序保证从新浪获取持仓的最新tick。若没有，则认为是停牌。
                continue

            preClose = self._posCloses.get(tick.code)
            if preClose is None:
                info.print('交易接口[{0}]: 持仓{1}({2})没有收盘价[{3}]数据'.format(self.brokerName, tick.code, tick.name, self._posDate), DyLogData.error)
                continue

            adjFactor = tick.preClose/preClose

            pos[2] /= adjFactor
            pos[3] /= adjFactor
            pos[6] *= adjFactor

            pos[-1] = '否' if adjFactor == 1 else '是'

        # If xrxd, need to update again
        # Here for simplicity, no matter xrxd or not, always update.
        self.__updatePerTicks(ticks)

        # trigger synchronize positions event
        self._posSync = True
        super().syncPos()

    def onTicks(self, ticks):
        """
            For UI
            update stock price related data, e.g. stock market value, stock price, PnL
        """
        self.__updatePerTicks(ticks)
        
        self.__syncPos(ticks)

    def syncPos(self):
        """
            模拟账户的持仓只能根据实时行情计算
        """
        # 有持仓，则需要根据实时tick才能同步持仓
        if self._posCloses:
            return

        # 没有持仓，则直接认为同步成功。
        self._posSync = True
        super().syncPos()


################################################## 模拟交易子类 ##################################################
################################################## 模拟交易子类 ##################################################
################################################## 模拟交易子类 ##################################################
class SimuTrader1(SimuTrader):
    brokerName = '模拟1'
    broker = 'simu1'

    accountPath = 'Stock/Program/Broker/{0}'.format(brokerName)
    
    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)


class SimuTrader2(SimuTrader):
    brokerName = '模拟2'
    broker = 'simu2'

    accountPath = 'Stock/Program/Broker/{0}'.format(brokerName)
    
    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)


class SimuTrader3(SimuTrader):
    brokerName = '模拟3'
    broker = 'simu3'

    accountPath = 'Stock/Program/Broker/{0}'.format(brokerName)
    
    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)


class SimuTrader4(SimuTrader):
    brokerName = '模拟4'
    broker = 'simu4'

    accountPath = 'Stock/Program/Broker/{0}'.format(brokerName)
    
    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)


class SimuTrader5(SimuTrader):
    brokerName = '模拟5'
    broker = 'simu5'

    accountPath = 'Stock/Program/Broker/{0}'.format(brokerName)
    
    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)


class SimuTrader6(SimuTrader):
    brokerName = '模拟6'
    broker = 'simu6'

    accountPath = 'Stock/Program/Broker/{0}'.format(brokerName)
    
    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)

class SimuTrader7(SimuTrader):
    brokerName = '模拟7'
    broker = 'simu7'

    accountPath = 'Stock/Program/Broker/{0}'.format(brokerName)
    
    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)

class SimuTrader8(SimuTrader):
    brokerName = '模拟8'
    broker = 'simu8'

    accountPath = 'Stock/Program/Broker/{0}'.format(brokerName)
    
    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)

class SimuTrader9(SimuTrader):
    brokerName = '模拟9'
    broker = 'simu9'

    accountPath = 'Stock/Program/Broker/{0}'.format(brokerName)
    
    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)



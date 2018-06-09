import copy
import os
from collections import OrderedDict
from datetime import *

from DyCommon.DyCommon import *
from ..DyStockTradeCommon import *
from ..DyStockStrategyBase import *
from ..AccountManager.DyStockPos import *
from ...Select.Engine.DyStockSelectSelectEngine import *


class DyStockCtaTemplate(object):
    """
        CTA策略模板， 所有CTA策略的基类，其实非CTA策略也可以使用。
        !!!如果策略中要使用时间，务必使用ETF300，因为指数没有tick历史数据。
        如果只是为了UI显示，则不需要。
        使用ETF300可以做到实盘和回测的统一。由于沪市比深市tick更新慢，所以实盘可能会有比较小的时差。
        回测和实盘引擎，默认会监听ETF300和ETF500。
    """

    name = 'DyStockCtaTemplate'
    chName = 'CTA策略模板'

    #--------------------- 仓控相关 ---------------------
    # 按比例买卖的constants
    cCodePos = '个股持仓市值' # 基于特定个股持仓市值
    cPos = '持仓市值' # 基于持仓市值，所有持仓个股
    cAccountCapital = '账户总资产' # 基于账户总资产，持仓市值 + 现金（可使用）
    cAccountCash = '账户现金' # 基于账户现金（可使用）
    cAccountLeftCashRatio = '账户剩余资金比例' # 基于账户剩余现金（可使用）占比总资金的比例。比如50，意思就是账户剩余的资金占比总资产的50%。
    cFixedCash = '固定现金' # 固定现金额度，若为20000，意味着买入20000金额的股票

    allowSmallCashBuy = False # 允许策略小资金买入

    #--------------------- 窗口UI相关 ---------------------
    param = None # 策略回测窗口配置参数

    # 数据
    dataHeader = None # 实时数据窗口表头
    maxUiDataRowNbr = None # UI显示的最大数据行数，为了提高UI的刷新效率，有时显示太多数据，也没有太大用处

    # 指示
    # 策略中两个信号相关的变量:
    #   @signalInfo: 信号信息，回测时使用，这个值由@signalDetails转换而来。类型: string
    #   @signalDetails: 信号明细，实盘时使用。必须符合表格式@signalDetailsHeader。类型: []。
    #                   信号明细只是指策略产生信号，并不关心交易成功。交易成功跟很多因素有关，比如风控，资金，网络接口等等。
    opHeader = ['时间', '类型', '代码', '名称', '价格', '数量(股)', '卖出原因', '成本', '预计盈亏比(%)', '预计盈亏(元)'] # 实时操作窗口表头
    opHeaderCodePos = opHeader.index('代码')
    signalDetailsHeader = None # 实时信号明细窗口表头, 子类改写时。由于信号分买入和卖出，所以此表头字段是买入和卖出信号明细的并集。

    #--------------------- 运行模式相关 ---------------------
    backTestingMode = 'tick' # 回测模式，e.g. tick, bar1d, bar1m, bar5m, ... 最大低频支持日线级别
    liveMode = 'tick' # 实盘模式

    #--------------------- 实盘相关 ---------------------
    broker = None # 实盘交易接口, like 'gtja'。由实盘的子类改写。None: 不支持实盘

    # 实盘时，策略使用的买入和卖出价，为了容易成交
    # !!!注意：一部分策略的参数放在了DyStockTradeCommon类里
    buyPrice = 'askPrice1' # 买入使用价，即五档的卖盘
    sellPrice = 'bidPrice1' # 卖出使用价，即五档的买盘

    #--------------------- 风控相关 ---------------------
    curCodeBuyMaxNbr = None # 当日相同标的买入最大次数，None：无限制

    #--------------------- 其他 ---------------------
    push2Internet = False
    enableBuy = True # 打开买入开关，若关闭，买入信号的通知信息也不会发出
    enableQuery = True # 是否支持微信的查询请求，主要是输入'1'时的查询


    #--------------------- 私有类变量 ---------------------
    __stockSelectEngine = None # 选股引擎，为了对接选股后的实盘


    def __init__(self, ctaEngine, info, state, strategyParam=None):
        """
            @state: 策略状态
            @strategyParam: 策略参数。 实盘时是None；回测时，会从策略窗口生成策略参数
        """
        self._ctaEngine = ctaEngine
        self._info = info
        self._state = state
        self._strategyParam = strategyParam

        # 初始化当日相关数据
        self.__curInit()

    def __curInit(self, date=None):
        """
            初始化当日相关数据，被子类继承
        """
        self._curTDay = date # 当前交易日, 由子类重新赋值

        self._monitoredStocks = [] # 由策略在onOpen里面赋值

        self._curPos = OrderedDict() # 策略的当前持仓, {code: DyStockPos}，策略的持仓主要是为了知道策略买了多少股票和及时市值，其它并不关注
        self._curEntrusts = OrderedDict() # 策略的今日委托, {dyEntrustId: DyStockEntrust}
        self._curDeals = OrderedDict() # 策略的今日成交, {dyDealId: DyStockDeal}

        self._curNotDoneEntrusts = {} # 策略的今日未完成委托，为了提高效率，{code: {dyEntrustId: DyStockEntrust}}

        self._preparedData = {} # 策略开盘准备数据，由策略决定格式
        self._preparedPosData = {} # 为持仓股票准备的数据，一般格式为{pos code: data}

        self._preSavedData = {} # 昨日策略保存的数据，持仓除外
        self._curSavedData = {} # 当日策略要保存的数据，只在@onClose里使用

        # risk related
        self._curCodeBuyCountDict = {} # {code: buy count}，当日标的的买入次数字典

        self._posSync = False # 策略持仓是否已经跟账户同步过
    
    def _loadOnClose(self):
        """
            载入前一交易日策略的收盘保存数据
        """
        # 从磁盘载入策略收盘保存数据
        savedData = self._ctaEngine.loadOnClose(self._curTDay, self.__class__)
        if not savedData:
            return

        # 创建策略持仓
        if 'pos' in savedData:
            positions = savedData['pos']
            for code, pos in positions.items():
                self._curPos[code] = DyStockPos.restorePos(pos, self.__class__)

            del savedData['pos']

        # 保存持仓之外的数据
        self._preSavedData = savedData

    def onOpenCodes(self):
        """
            策略开盘关注的股票代码（由用户选择继承实现）
            主要是为了策略开盘前的@prepare。回测优化参数时，target codes是动态生成的，所以需要此接口。
            @return: [code] or None
        """
        return None

    def onOpenWrapper(func):
        """
            子类@onOpen的装饰器
        """
        def wrapper(self, *args, **kwargs):

            # 调用父类的@onOpen
            if not super(self.__class__, self).onOpen(*args, **kwargs):
                return False

            return func(self, *args, **kwargs)

        return wrapper

    def onOpen(self, date, codes=None):
        """
            初始化策略每天开盘前的数据，这些数据都与当日有关（必须由用户继承实现）
                - prepared data，准备数据
                - prepared positions data，策略持仓准备数据
                - positions，持仓
                - 当日相关数据
            基类里的@onOpen主要是为了初始化策略的共同数据
            @codes: 由@onOpenCodes提供
            @return: bool
        """
        # 初始化当日相关数据
        self.__curInit(date)

        # 载入策略开盘准备数据
        self._preparedData = self.loadPreparedData(date, codes=codes)
        if self._preparedData is None:
            return False

        # !!!先载入前一交易日策略的保存数据
        self._loadOnClose()

        # 载入为持仓股票准备的数据
        self._preparedPosData = self.loadPreparedPosData(date, posCodes=list(self._curPos) if self._curPos else None)
        if self._preparedPosData is None:
            return False

        self._monitoredStocks.extend(list(self._curPos))

        return True

    def onMonitor(self):
        """
            引擎获取策略开盘前要监控的股票（必须由用户赋值@self._monitoredStocks）
            之所以不需要子类重载此接口是因为子类重载也需要定义list，然后添加code到list里，最后返回list。
            这样子类的@onMonitor实现其实都是一样的，都是返回监控股票列表。
            返回值：股票列表
        """
        return self._monitoredStocks

    def onTicksWrapper(func):
        """
            子类@onTicks的装饰器
        """
        def wrapper(self, ticks):
            # 先更新持仓
            for code, pos in self._curPos.items():
                tick = ticks.get(code)
                if tick is not None:
                    pos.onTick(tick)

            func(self, ticks)

        return wrapper

    def onTicks(self, ticks):
        """
            收到行情Ticks推送（Tick模式下，必须由用户继承实现）
            新浪行情是一次性抓取所有监控的股票，策略引擎会过滤成策略关注的股票池。
            @ticks: {code: DyStockCtaTickData}
        """
        raise NotImplementedError

    def onBarsWrapper(func):
        """
            子类@onBars的装饰器
        """
        def wrapper(self, bars):
            # 先更新持仓
            for code, pos in self._curPos.items():
                bar = bars.get(code)
                if bar is not None:
                    pos.onBar(bar)

            func(self, bars)

        return wrapper

    def onBars(self, bars):
        """
            收到行情Bars推送（Bar模式下，必须由用户继承实现）
            @bars: {code: DyStockCtaBarData}
        """
        raise NotImplementedError

    def onStop(self):
        """ 停止策略（必须由用户继承实现）"""
        raise NotImplementedError

    def onCloseWrapper(func):
        """
            子类@onClose的装饰器
        """
        def wrapper(self, *args, **kwargs):
            func(self, *args, **kwargs)

            # 调用父类的@onClose
            super(self.__class__, self).onClose(*args, **kwargs)

        return wrapper

    def _onClosePos(self):
        codes = list(self._curPos)
        for code in codes:
            if self._curPos[code].totalVolume == 0:
                del self._curPos[code]

        for _, pos in self._curPos.items():
            pos.onClose()

    def onClose(self):
        """
            策略每天收盘后的数据处理（由用户选择继承实现）
            持仓数据由策略模板类负责保存
            其他收盘后的数据，则必须由子类实现（即保存到@self._curSavedData）
        """
        # 更新持仓收盘
        self._onClosePos()

        # get saved data of positions
        positions = {}
        for code, pos in self._curPos.items():
            positions[code] = pos.getSavedData()

        # add into saved data
        if positions:
            self._curSavedData['pos'] = positions

        self._ctaEngine.saveOnClose(self._curTDay, self.__class__, self._curSavedData)

    @classmethod
    def prepare(cls, date, dataEngine, info, codes=None, errorDataEngine=None, strategyParam=None, isBackTesting=False):
        """
            类方法，策略开盘前的准备数据（由用户选择继承实现）
            @date: 前一交易日。由当日交易调用，@date为当日的前一交易日。
            @strategyParam: 策略参数，回测时有效
            @return: None-prepare错误, {}-策略没有准备数据
        """
        return {}

    @classmethod
    def preparePos(cls, date, dataEngine, info, posCodes=None, errorDataEngine=None, strategyParam=None, isBackTesting=False):
        """
            类方法，策略开盘前的持仓准备数据（由用户选择继承实现）
            @date: 前一交易日。由当日交易调用，@date为当日的前一交易日。
            @posCodes: list, None-没有持仓
            @return: None-prepare position data错误, {}-策略没有持仓准备数据
        """
        return {}
    
    def getBuyVol(self, cash, code, price):
        return self._ctaEngine.getBuyVol(cash, code, price)

    @classmethod
    def value2Str(cls, value):
        """
            类公共方法
            主要是为了UI和即时通讯的显示
        """
        if value is None:
            value = ''
        else:
            if isinstance(value, float):
                if not np.isnan(value):
                    value = '%.2f'%value
                else:
                    value = ''

        return str(value)

    def __convert2SignalInfo(self, signalDetails=None):
        """
            回测时，将实盘推送给UI的信号明细转成对应的信号信息
            @signalDetails: []
            @signalInfo: string
        """
        if signalDetails is None:
            return None

        if not self._state.isState(DyStockStrategyState.backTesting):
            return None

        signalInfo = ''
        for name, value in zip(self.signalDetailsHeader, signalDetails):
            value = self.value2Str(value)
            if value:
                if signalInfo:
                    signalInfo += ','

                signalInfo += '{0}:{1}'.format(name, value)

        return signalInfo

    def __checkBuy(self, tick):
        """
            买入前的检查
        """
        # risk control，需要考虑回测和实盘运行时
        # 控制同一标的的买入次数
        self._curCodeBuyCountDict.setdefault(tick.code, 0)
        self._curCodeBuyCountDict[tick.code] += 1

        if self.curCodeBuyMaxNbr is not None and \
            not self._state.isState(DyStockStrategyState.monitoring) and \
            self._curCodeBuyCountDict[tick.code] > self.curCodeBuyMaxNbr:
            return False

        return True

    def buy(self, tick, volume, signalDetails=None, price=None):
        """
            委托买入
            不管交易成功与否，信号明细总是推送给UI。目的是让UI或者即时通讯知道策略产生了信号。
            半自动交易时，用来提示。
            @price: 限价买入。若没有指定，则由策略基于Tick决定买入价格
            @signalDetails: [], 信号明细，回测时会转换成信号信息
            @return: entrust or None。None-失败或者在监控状态都不会生成委托实例。关心这个返回值的策略，要注意什么情况下是None。
        """
        if not self.enableBuy:
            return None

        # 不管买入成功与否，首先推送信号明细到UI
        self.putStockMarketMonitorUiEvent(signalDetails=None if signalDetails is None else [signalDetails])

        if not self.__checkBuy(tick):
            return None

        entrust = self._ctaEngine.buy(self.__class__, tick, volume, self.__convert2SignalInfo(signalDetails), price)
        if entrust is not None:
            self._curEntrusts[entrust.dyEntrustId] = entrust

            self._add2CurNotDoneEntrusts(entrust)

        return entrust
    
    def sell(self, tick, volume, sellReason=DyStockSellReason.strategy, signalDetails=None, price=None):
        """
            @signalDetails: [], 信号明细，回测时会转换成信号信息
        """
        # 不管卖出成功与否，首先推送信号明细到UI
        self.putStockMarketMonitorUiEvent(signalDetails=None if signalDetails is None else [signalDetails])

        # 二次保护，防止卖出其他策略的仓位
        if self.getCodePosAvailVolume(tick.code) < volume:
            return None

        entrust = self._ctaEngine.sell(self.__class__, tick, volume, sellReason, self.__convert2SignalInfo(signalDetails), price)
        if entrust is not None:
            self._curEntrusts[entrust.dyEntrustId] = entrust

            self._add2CurNotDoneEntrusts(entrust)

        return entrust

    def cancel(self, code=None):
        """
            撤销委托
            @code: None-撤销所有未完成的委托
            @return: bool, True if all are true else False。如果指定code，没有发生一次撤销，则认为是失败。
        """
        if code is None:
            ret = True
            for _, entrusts in self._curNotDoneEntrusts.items():
                for _, entrust in entrusts.items():
                    # 撤销委托
                    ret = self._ctaEngine.cancel(self.__class__, entrust) and ret

        else:
            entrusts = self._curNotDoneEntrusts.get(code)
            if entrusts is None:
                ret = False
            else:
                ret = True
                for _, entrust in entrusts.items():
                    # 撤销委托
                    ret = self._ctaEngine.cancel(self.__class__, entrust) and ret

        return ret

    def closePos(self, tick, sellReason=DyStockSellReason.strategy, signalDetails=None):
        """
            @signalDetails: [], 信号明细，回测时会转换成信号信息
        """
        # 不管卖出成功与否，首先推送信号明细到UI
        self.putStockMarketMonitorUiEvent(signalDetails=None if signalDetails is None else [signalDetails])

        # get code position of strategy
        volume = self.getCodePosAvailVolume(tick.code)
        if volume == 0:
            return None

        # close position
        entrust = self._ctaEngine.closePos(self.__class__, tick, volume, sellReason, self.__convert2SignalInfo(signalDetails))
        if entrust is not None:
            self._curEntrusts[entrust.dyEntrustId] = entrust

            self._add2CurNotDoneEntrusts(entrust)

        return entrust

    def buyByRatio(self, tick, ratio, ratioMode, signalDetails=None):
        """
            按照比例买入股票：
                基于个股持仓市值
                基于持仓市值
                基于账户总资产
                基于账户现金
                ...

            仓位计算，完全由引擎控制，简化策略仓位控制
            @ratio: % 或者是现金值
            @signalDetails: [], 信号明细，回测时会转换成信号信息
        """
        if not self.enableBuy:
            return None

        # 不管买入成功与否，首先推送信号明细到UI
        self.putStockMarketMonitorUiEvent(signalDetails=None if signalDetails is None else [signalDetails])

        if not self.__checkBuy(tick):
            return None

        entrust = self._ctaEngine.buyByRatio(self.__class__, tick, ratio, ratioMode, self.__convert2SignalInfo(signalDetails))
        if entrust is not None:
            self._curEntrusts[entrust.dyEntrustId] = entrust

            self._add2CurNotDoneEntrusts(entrust)

        return entrust

    def sellByRatio(self, tick, ratio, ratioMode, sellReason=DyStockSellReason.strategy, signalDetails=None):
        """
            按照比例卖出股票
            @ratio: %
            @signalDetails: [], 信号明细，回测时会转换成信号信息
        """
        # 不管卖出成功与否，首先推送信号明细到UI
        self.putStockMarketMonitorUiEvent(signalDetails=None if signalDetails is None else [signalDetails])

        entrust = self._ctaEngine.sellByRatio(self, tick, ratio, ratioMode, sellReason, self.__convert2SignalInfo(signalDetails))
        if entrust is not None:
            self._curEntrusts[entrust.dyEntrustId] = entrust

            self._add2CurNotDoneEntrusts(entrust)

        return entrust

    def putEvent(self, type, data):
        """
            推送一个事件到事件引擎
            @type: 事件类型
            @data: 事件数据，一般为dict
        """
        self._ctaEngine.putEvent(type, data)

    def putStockMarketMonitorUiEvent(self, data=None, newData=False, op=None, signalDetails=None, datetime_=None):
        """
            参数说明参照DyStockCtaEngine
            @datetime_: 行情数据时有效
        """
        self._ctaEngine.putStockMarketMonitorUiEvent(self.__class__, data, newData, op, signalDetails, datetime_)

    def putStockMarketStrengthUpdateEvent(self, time, marketStrengthInfo):
        if time is None:
            return

        self._ctaEngine.putStockMarketStrengthUpdateEvent(self.__class__, time, marketStrengthInfo.copy())

    def loadPreparedData(self, date, codes=None):
        """
            策略开盘前载入所需的准备数据和策略实例属性。在策略的@onOpen实现里被调用。
            若磁盘没有准备数据，则实时生成
            @date: 当日
        """
        isBackTesting = self._state.isState(DyStockStrategyState.backTesting)

        if not isBackTesting:
            self._info.print('载入策略的准备数据...')

        # load from JSON file
        data = self._ctaEngine.loadPreparedData(date, self.__class__)
        if data is None:
            if not isBackTesting:
                self._info.print('策略的准备数据载入失败', DyLogData.warning)
                self._info.print('开始实时准备策略开盘前数据...')

            # 前一日
            date = self._ctaEngine.tDaysOffsetInDb(DyTime.getDateStr(date, -1))

            # prepare
            data = self.prepare(date, self._ctaEngine.dataEngine, self._info, codes, self._ctaEngine.errorDataEngine, self._strategyParam, isBackTesting)
            try:
                data = json.loads(json.dumps(data)) # Sometime there're non-python objects in @data, use this tricky way to convert to python objects.
            except:
                pass

            if not isBackTesting:
                self._info.print('实时准备策略开盘前数据完成')
        else:
            if not isBackTesting:
                self._info.print('策略的准备数据载入完成')
            
        return data

    def loadPreparedPosData(self, date, posCodes=None):
        """
            策略开盘前载入所需的持仓准备数据。在策略的@onOpen实现里被调用。
            若磁盘没有准备数据，则实时生成
            @date: 当日
        """
        isBackTesting = self._state.isState(DyStockStrategyState.backTesting)

        if not isBackTesting:
            self._info.print('载入策略的持仓准备数据...')

        # load from JSON file
        data = self._ctaEngine.loadPreparedPosData(date, self.__class__)
        if data is None:
            if not isBackTesting:
                self._info.print('策略的持仓准备数据载入失败', DyLogData.warning)
                self._info.print('开始实时准备策略开盘前持仓数据...')

            # 前一日
            date = self._ctaEngine.tDaysOffsetInDb(DyTime.getDateStr(date, -1))

            # prepare
            data = self.preparePos(date, self._ctaEngine.dataEngine, self._info, posCodes, self._ctaEngine.errorDataEngine, self._strategyParam, isBackTesting)
            try:
                data = json.loads(json.dumps(data)) # Sometime there're non-python objects in @data, use this tricky way to convert to python objects.
            except:
                pass

            if not isBackTesting:
                self._info.print('实时准备策略开盘前持仓数据完成')
        else:
            if not isBackTesting:
                self._info.print('策略的持仓准备数据载入完成')
            
        return data

    def getPreparedDataBySelectStrategy(date, dataEngine, selectStrategyCls, param, codes=None):
        """
            运行选股策略，获得策略实盘或者回测准备数据。既然是策略准备数据，则是前一交易日的数据。
            这个接口由策略类prepare函数调用。
            
            @date: 前一交易日。由当日交易调用，@date为当日的前一交易日。
            @dataEngine: 数据引擎，主要为了获取程序主Event Engine和Info
            @selectStrategyCls: 选股策略类
            @param: 选股策略的参数
            @codes: 选股引擎需要载入的股票代码表，None为所有股票。从选股引擎的角度讲，为测试股票代码。

            @return: 策略准备数据字典
        """
        if DyStockCtaTemplate.__stockSelectEngine is None:
            DyStockCtaTemplate.__stockSelectEngine = DyStockSelectSelectEngine(dataEngine.eventEngine, dataEngine.info, registerEvent=False)

        # always set test codes
        DyStockCtaTemplate.__stockSelectEngine.setTestedStocks(codes)

        param['基准日期'] = date
        param['forTrade'] = None # 为了实盘的选股
        param['forTradeNoJson'] = None # 为了实盘的选股，但无需生成实盘选股的JSON文件。
                                       #!!! 这里有重复，实盘选股的JSON文件既可以通过选股窗口‘实盘选股’生成，又可以通过股票数据窗口的‘数据->生成实盘策略准备数据...’生成

        if not DyStockCtaTemplate.__stockSelectEngine.runStrategy(selectStrategyCls, param):
            return None

        return DyStockCtaTemplate.__stockSelectEngine.resultForTrade

    def onPos(self, positions):
        """
            券商账户持仓更新事件
            主要更新成本价，这样策略可以执行某些停损算法。
            成本价为券商账户里的持仓成本价，不是策略持仓的成本价。
        """
        for code, pos in self._curPos.items():
            newPos = positions.get(code)
            if newPos is None:
                continue

            pos.cost = newPos.cost

    def onEntrust(self, entrust):
        """
            委托状态更新事件
            !!!若策略需要知道对应委托的具体数据，必须通过@entrust.dyEntrustId获取对应的entrust实例。
            因为这里entrust实例改变了。
        """
        self._curEntrusts[entrust.dyEntrustId] = entrust

        self._tryRemoveFromCurNotDoneEntrusts(entrust)

    def onDeal(self, deal):
        """ 成交事件 """
        # 防止同一成交推送多次
        if deal.dyDealId in self._curDeals:
            return

        # add into current deal dict
        self._curDeals[deal.dyDealId] = deal

        #----- update positions -----
        # new position
        if deal.code not in self._curPos:
            if deal.type == DyStockOpType.buy: # the type should be buy, if not means some error.
                pos = DyStockPos(deal.datetime, self.__class__, deal.code, deal.name, deal.price, deal.volume)
                pos.sync = True
                pos.priceAdjFactor = 1
                pos.volumeAdjFactor = 1

                self._curPos[deal.code] = pos

            else:
                self._info.print('策略[{0}]的成交单[{1}], 成交类型不匹配'.format(self.chName, deal.dyDealId), DyLogData.error)

            return

        # buy
        if deal.type == DyStockOpType.buy:
            self._curPos[deal.code].addPos(deal.datetime, self.__class__, deal.price, deal.volume)
        else: # sell
            # we don't delete pos if total volume is 0, which will be done after market close.
            self._curPos[deal.code].removePos(deal.price, deal.volume)

    def canBuy(self, tick):
        """
            可以买入吗？
            防止涨停买不到
            不适合打板和排板策略，所以此函数由策略自己控制是否使用。
        """
        if tick is None:
            return False

        if tick.askPrices is None: # 回测
            if (tick.price - tick.preClose)/tick.preClose*100 >= DyStockCommon.limitUpPct:
                return False

        else: # 实盘
            if tick.askPrices[0] == 0: # 涨停并且卖1没有挂单
                return False

        return True

    def _add2CurNotDoneEntrusts(self, entrust):
        entrusts = self._curNotDoneEntrusts.setdefault(entrust.code, {})

        assert entrust.dyEntrustId not in entrusts
        entrusts[entrust.dyEntrustId] = entrust

    def _tryRemoveFromCurNotDoneEntrusts(self, entrust):
        """
            尝试删除已经完成的委托
        """
        if not entrust.isDone():
            return

        entrusts = self._curNotDoneEntrusts.get(entrust.code)
        if entrusts is None:
            return

        if entrust.dyEntrustId in entrusts:
            del entrusts[entrust.dyEntrustId]

        if not entrusts:
            del self._curNotDoneEntrusts[entrust.code]

    ################################## 仓位相关 ##################################
    ################################## 仓位相关 ##################################
    def syncPos(self, syncData):
        """
            由于除权除息的原因，从券商管理类同步策略持仓数据
        """
        # 不根据策略的self._posSync is True直接返回，而是根据持仓的同步标识
        # 回测时，由于数据问题可能会有某个持仓数据的暂时性缺失
        self._posSync = True

        for code, pos in self._curPos.items():
            if pos.sync:
                continue

            data = syncData.get(code)
            if data is None:
                if not self._state.isState(DyStockStrategyState.backTesting):
                    self._info.print('策略[{}]持仓同步失败: {}[{}]'.format(self.chName, pos.name, code), DyLogData.error)
                continue

            priceAdjFactor = data['priceAdjFactor']
            volumeAdjFactor = data['volumeAdjFactor']

            pos.cost = data['cost']

            pos.high /= priceAdjFactor
            if pos.closeHigh:
                pos.closeHigh /= priceAdjFactor

            pos.totalVolume *= volumeAdjFactor
            pos.availVolume *= volumeAdjFactor

            if priceAdjFactor != 1:
                pos.xrd = True

            pos.priceAdjFactor = priceAdjFactor
            pos.volumeAdjFactor = volumeAdjFactor

            pos.sync = True

    def getCodePosOverCapital(self, code):
        """
            获取指定股票的持仓占比券商账户总资产(%)
        """
        codePosMarketValue = self._ctaEngine.getCurCodePosMarketValue(self.__class__, code)
        if codePosMarketValue is None:
            return None

        capital = self._ctaEngine.getCurCapital(self.__class__)
        if capital is None or capital <= 0:
            return None

        return codePosMarketValue/capital*100

    def getCashOverCapital(self):
        """
            获取现金占比券商账户总资产(%)
        """
        cash = self.curCash
        if cash is None:
            return None

        capital = self._ctaEngine.getCurCapital(self.__class__)
        if capital is None or capital <= 0:
            return None

        return cash/capital*100

    def getCodePosAvailVolume(self, code):
        """
            获取策略持仓的可卖股数
        """
        pos = self._curPos.get(code)
        if pos is None:
            return 0

        return pos.availVolume

    def getCodePosTotalVolume(self, code):
        """
            获取策略持仓的总股数
        """
        pos = self._curPos.get(code)
        if pos is None:
            return 0

        return pos.totalVolume

    def processPreparedDataAdjWrapper(func):
        """
            子类@_processPreparedDataAdj的装饰器
            @self._preparedData的格式必须是如下形式：
                {'preClose': {code: preClose},
                'key': {code: value} # value can be single value, list, dict or object, 由策略自己解释
                }
        """
        def wrapper(self, tick):
            # We always return True, strategy should care about code of prepared data consistent with monitored ticks.
            preCloses = self._preparedData.get('preClose')
            if preCloses is None:
                return True

            preClose = preCloses.get(tick.code)
            if preClose is None:
                return True

            # 已经处理过除复权或者股票当日没有除权除息
            if tick.preClose == preClose:
                return True

            func(self, tick, preClose)

            # set back, so that we don't need to do it next time
            preCloses[tick.code] = tick.preClose

            return True

        return wrapper

    def processPreparedPosDataAdjWrapper(func):
        """
            子类@_processPreparedPosDataAdj的装饰器
            @self._preparedPosData的格式必须是如下形式：
                {code: {'preClose': preClose,
                        key: value # value can be single value, list, dict or object, 由策略自己解释
                        }
                }
        """
        def wrapper(self, tick):
            posData = self._preparedPosData.get(tick.code)
            if posData is None:
                return True

            # We always return True, strategy should care about code of prepared pos data consistent with positions.
            preClose = posData.get('preClose')
            if preClose is None:
                return True

            # 已经处理过除复权或者股票当日没有除权除息
            if tick.preClose == preClose:
                return True

            # 检查券商的前复权算法是不是与新浪一致。模拟账户不存在此问题，都是相同的前复权算法。
            # 实盘时，券商的复权因子会早于OnTicks.
            pos = self._curPos.get(tick.code)
            if pos and pos.sync:
                priceAdjFactor = preClose/tick.preClose
                if pos.priceAdjFactor != priceAdjFactor:
                    self._info.print('策略[{}]: 复权因子-新浪({})与{}({})不一致'.format(self.chName, priceAdjFactor, DyStockTradeCommon.accountMap[self.broker], pos.priceAdjFactor), DyLogData.warning)

            # call strategy adj function
            func(self, tick, preClose)

            # set back, so that we don't need to do it next time
            posData['preClose'] = tick.preClose

            return True

        return wrapper

    def processDataAdj(self, tick, preClose, dictData, keys, isPrice=True, keyCodeFormat=True):
        """
            处理一只股票数据的前复权。数据支持类型None，list，float，int，DataFrame，Series
            @tick: 股票Tick数据
            @preClose: 来自数据库的股票前一日收盘价
            @dictData: 字典数据，一般为@self._preparedData or @self._preparedPosData
            @keys: [key], 对哪些字典数据前复权
            @isPrice: 数据是价格相关的还是成交量相关的
            @keyCodeFormat: True - @dictData数据的格式是{key: {code: [] or x}}
                            False - @dictData数据的格式是{code: {key: [] or x}}
        """
        code = tick.code

        # 复权因子
        if isPrice:
            adjFactor = tick.preClose/preClose
        else:
            adjFactor = preClose/tick.preClose

        if keyCodeFormat:
            for key in keys:
                data = dictData.get(key)
                if data is None:
                    continue

                data_ = data.get(code)
                if data_ is None:
                    continue

                if isinstance(data_, list):
                    data_[:] = list(map(lambda x, y: x*y, data_, [adjFactor]*len(data_)))
                else:
                    data[code] = data_*adjFactor

        else:
            data = dictData.get(code)
            if data is not None:
                for key in keys:
                    data_ = data.get(key)
                    if data_ is None:
                        continue

                    if isinstance(data_, list):
                        data_[:] = list(map(lambda x, y: x*y, data_, [adjFactor]*len(data_)))
                    else:
                        data[key] = data_*adjFactor

    def processOhlcvDataAdj(self, tick, preClose, dictData, key, keyCodeFormat=True):
        """
            处理一只股票OHLCV数据的前复权
            @tick: 股票Tick数据
            @preClose: 来自数据库的股票前一日收盘价，为了计算复权因子
            @dictData: 字典数据，一般为@self._preparedData or @self._preparedPosData
            @key: 字典数据对应的key
            @keyCodeFormat: True - @dictData数据的格式是{key: {code: [OHLCV] or [[OHLCV]]}}
                            False - @dictData数据的格式是{code: {key: [OHLCV] or [[OHLCV]]}}
        """
        code = tick.code

        # 复权因子
        adjFactor = tick.preClose/preClose

        if keyCodeFormat:
            data = dictData.get(key)
            if data is not None:
                data = data.get(code)
        else:
            data = dictData.get(code)
            if data is not None:
                data = data.get(key)

        if data:
            # 检查数据的维数
            if not isinstance(data[0], list): # 一维
                data = [data] # 改成二维

            # 前复权
            for dayData in data:
                for i in range(4): # price related
                    dayData[i] *= adjFactor

                dayData[-1] /= adjFactor # volume


    ################################## 属性 ##################################
    ################################## 属性 ##################################
    @property
    def curPos(self):
        return self._curPos

    @property
    def curEntrusts(self):
        return self._curEntrusts

    @property
    def curDeals(self):
        return self._curDeals

    @property
    def curCash(self):
        """
            策略没有固定分配好的资金。采用共享账户资金池的方式。
            这里并不关心策略的运行状态，只是返回对应账户的数据
        """
        return self._ctaEngine.getCurCash(self.__class__)

    @property
    def state(self):
        """
            @策略状态对象：监控，运行和回测
        """
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    @property
    def marketTime(self):
        return self._ctaEngine.marketTime

    @property
    def marketDatetime(self):
        return self._ctaEngine.marketDatetime

    @property
    def indexTick(self):
        return self._ctaEngine.indexTick

    @property
    def etf300Tick(self):
        return self._ctaEngine.etf300Tick

    @property
    def etf500Tick(self):
        return self._ctaEngine.etf500Tick

    def getEtfTick(self, code):
        if code == DyStockCommon.etf300:
            return self.etf300Tick

        return self.etf500Tick

    def getCurCodeBuyCount(self, code):
        """
            获取当日股票的买入次数
        """
        return self._curCodeBuyCountDict.get(code, 0)
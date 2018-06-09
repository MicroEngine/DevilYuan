class DyEventType:

    # ----- used by system -----
    register = 'eRegister'
    registerTimer = 'eRegisterTimer'
    unregister = 'eUnregister'
    unregisterTimer = 'eUnregisterTimer'


    # ----- common event -----
    timer = 'eTimer_' # actually, timer event will like 'eTimer_3', which means timer with 3s interval

    log = 'eLog'
    progressTotal = 'eProgessTotal'
    progressSingle = 'eProgressSingle'

    subLog_ = 'eSubLog_' # + period
    subProgressTotal_ = 'eSubProgessTotal_' # + period

    stopAck = 'eStopAck'
    fail = 'eFail'
    finish = 'eFinish' # 所有部分都完成
    finish_ = 'eFinish_' # 子部分完成


    # ----- DyStockTableWidget相关事件 -----

    # DyStockTableWidget Header相关事件
    stockTableAddColumnsActAck = 'eStockTableAddColumnsActAck'

    # DyStockTableWidget Item相关事件
    stockTableIndustryCompareActAck = 'eStockTableIndustryCompareActAck' # 从同花顺获取股票行业对比Ack事件


    # ----- 选股相关事件 -----
    stockSelectStrategySelectReq = 'eStockSelectStrategySelectReq' # 执行一个选股策略
    stockSelectStrategySelectAck = 'eStockSelectStrategySelectAck'
    stockSelectStrategyRegressionReq = 'eStockSelectStrategyRegressionReq' # 执行一个选股策略的回归
    stockSelectStrategyRegressionAck = 'eStockSelectStrategyRegressionAck'

    stockSelectTestedCodes = 'eStockSelectTestedCodes' # 调试股票事件

    plotReq = 'ePlotReq' # 画图请求事件, 具体画什么样的图由event.data['type']指定。主要由Viewer引擎，生成画图所需要的数据，然后Ack给UI画图。
    plotAck = 'ePlotAck' # 画图Ack事件


    # ----- 股票交易相关事件 -----

    # To Ui, 主要是策略数据行情，操作和信号明细的事件
    # 策略账户相关的事件则独立分开
    stockMarketMonitorUi = 'eStockMarketMonitorUi_' # stockMarketMonitorUi + strategy_name
    
    stockMarketStrengthUpdate = 'eStockMarketStrengthUpdate' # 来自于策略的股票市场强度更新事件
    stockMarketStrengthUpdateFromUi = 'eStockMarketStrengthUpdateFromUi' # 来自于UI的股票市场强度更新事件

    enableProxy = 'eEnableProxy' # 激活代理

    # To StockCtaEngine
    startStockCtaStrategy = 'eStartStockCtaStrategy'
    changeStockCtaStrategyState = 'eChangeStockCtaStrategyState'
    stopStockCtaStrategy = 'eStopStockCtaStrategy'

    stockMarketMonitor = 'eStockMarketMonitor' # 策略请求监控的股票池事件
    stockMarketTicks = 'eStockMarketTicks' # 股票池行情的Tick事件, 包含指数

    # QQ related
    startStockQQMsg = 'eStartStockQQMsg' # 开始QQ提醒
    stopStockQQMsg = 'eStopStockQQMsg' # 停止QQ提醒
    restartStockQQBot = 'eRestartStockQQBot'

    sendStockTestQQMsg = 'eSendStockTestQQMsg' # 发送股票测试QQ消息
    qqQueryStockStrategy = 'eQqQueryStockStrategy' # QQ查询股票策略实时信息

    # WeChat related
    startStockWx = 'eStartStockWx' # 开始微信提醒
    stopStockWx = 'eStopStockWx' # 停止微信提醒

    sendStockTestWx = 'eSendStockTestWx' # 发送股票测试微信
    wxQueryStockStrategy = 'eWxQueryStockStrategy' # 微信查询股票策略实时信息

    # RPC
    startStockRpc = 'eStartStockRpc' # 开始RPC
    stopStockRpc = 'eStopStockRpc' # 停止RPC

    # 一键挂机
    beginStockTradeDay = 'eBeginStockTradeDay' # 交易日开始
    endStockTradeDay = 'eEndStockTradeDay' # 交易日结束

    # 股票交易接口的事件（To券商）
    stockLogin = 'eStockLogin'
    stockLogout = 'eStockLogout'
    stockBuy = 'eStockBuy_' # 买入股票事件 + broker(English name)
    stockSell = 'eStockSell_'
    stockCancel = 'eStockCancel_' # 撤销委托

    # 推送给引擎的事件，由引擎分发给不同的策略
    stockOnEntrust = 'eStockOnEntrust' # 股票委托回报推送事件
    stockOnDeal = 'eStockOnDeal' # 股票成交回报推送事件

    # 股票持仓同步（更新）事件，一旦券商账户（DyStockAccountManager）有持仓更新，则发送此事件。
    # 主要目的是推送持仓成本价，这样策略可以根据成本价做停损处理。
    # !!!若多个策略持有同一只股票，但成本价只有一个。
    stockOnPos = 'eStockOnPos' # format: @event.data are {'broker': broker, 'pos': positions}

    # To UI的策略账户相关事件
    stockStrategyEntrustsUpdate = 'eStockStrategyEntrustsUpdate_' # 股票策略委托更新事件 + strategyCls.name
    stockStrategyDealsUpdate = 'eStockStrategyDealsUpdate_' # 股票策略委托更新事件 + strategyCls.name
    stockStrategyPosUpdate = 'eStockStrategyPosUpdate_' # 股票策略持仓更新事件 + strategyCls.name

    # 券商接口推送的原始数据的事件，需要做数据转换后，然后再选择推送给引擎
    stockCapitalUpdate = 'eStockCapitalUpdate_' # 账户资金状况更新事件 + broker(English name)
    stockPositionUpdate = 'eStockPositionUpdate_' # 账户持仓更新事件 + broker
    stockCurEntrustsUpdate = 'eStockCurEntrustsUpdate_' # 账户当日委托更新事件 + broker
    stockCurDealsUpdate = 'eStockCurDealsUpdate_' # 账户当日成交更新事件 + broker
    stockEntrustUpdate = 'eStockEntrustUpdate_' # 账户单个委托更新事件 + broker, 如果网络或者其他什么原因，可能会导致委托无法挂到券商，这时用此事件通知

    # 主要为了UI的更新
    stockCapitalTickUpdate = 'eStockCapitalTickUpdate_' # 账户资金状况每Tick更新事件 + broker(English name)
    stockPositionTickUpdate = 'eStockPositionTickUpdate_' # 账户持仓每Tick更新事件 + broker

    #!!! 以下是因为除复权引入的持仓更新事件
    # 主要更新持仓的复权因子和持仓成本价
    stockPosSyncFromBroker = 'eStockPosSyncFromBroker_' # 券商接口持仓同步事件 + broker(English name)，第一次启动券商接口会触发此事件
    stockPosSyncFromAccountManager = 'eStockPosSyncFromAccountManager' # 券商管理类的持仓同步事件，为了策略的持仓同步。启动券商接口或者启动策略会触发此事件。

    stockBrokerRetry = 'eStockBrokerRetry_' # 券商接口重试事件 + broker, 有些时候券商接口失败了，必须要重试直到成功

    # 策略手动买入相关事件，主要为了测试用
    stockStrategyMonitoredCodesReq = 'eStockStrategyMonitoredCodesReq' # 请求策略监控股票池代码事件
    stockStrategyMonitoredCodesAck = 'eStockStrategyMonitoredCodesAck'

    stockStrategyManualBuy = 'eStockStrategyManualBuy' # 策略手动买入事件，也就是说通过UI买入

    # 策略手动卖出相关事件，主要为了测试用
    stockStrategyPosReq = 'eStockStrategyPosReq' # 请求策略当前持仓事件
    stockStrategyPosAck = 'eStockStrategyPosAck'

    stockStrategyManualSell = 'eStockStrategyManualSell' # 策略手动卖出事件，也就是说通过UI卖出

    # 策略实盘相关事件
    stockStrategyOnOpen = 'eStockStrategyOnOpen' # 策略开盘事件，有些策略开盘可以将选出的股票推送出去，这样可以开盘前做一定的主观分析


    # ----- 股票数据相关事件 -----
    stockOneKeyUpdate = 'eStockOneKeyUpdate' # 一键更新
    stopStockOneKeyUpdateReq = 'eStopStockOneKeyUpdateReq' # 停止一键更新
    stockDaysCommonUpdateFinish = 'eStockDaysCommonUpdateFinish' # 股票日线通用数据更新结束, 也就是股票代码表和交易日数据

    # 股票历史tick数据更新相关事件
    stockHistTicksReq = 'eStockHistTicksReq_'
    stockHistTicksAck = 'eStockHistTicksAck'
    updateStockHistTicks = 'eUpdateStockHistTicks'
    stopUpdateStockHistTicksReq = 'eStopUpdateStockHistTicksReq'
    verifyStockHistTicks = 'eVerifyStockHistTicks'
    stopVerifyStockHistTicksReq = 'eStopVerifyStockHistTicksReq'

    updateHistTicksDataSource = 'eUpdateHistTicksDataSource' # 更新历史分笔数据源

    # 股票历史日线数据更新相关事件
    updateStockHistDays_ = 'eUpdateStockHistDays_' # 股票历史日线数据更新子事件, daysEngine内部使用
    updateStockHistDays = 'eUpdateStockHistDays' # 用户请求股票历史日线数据更新事件
    stopUpdateStockHistDaysReq = 'eStopUpdateStockHistDaysReq'

    updateStockSectorCodes = 'eUpdateStockSectorCodes' # 用户请求股票板块代码表更新事件

    # 策略数据准备
    stockStrategyDataPrepare = 'eStockStrategyDataPrepare'
    stopStockStrategyDataPrepareReq = 'eStopStockStrategyDataPrepareReq'


    # ----- 股票策略回测相关事件 -----
    stockStrategyBackTestingReq = 'eStockStrategyBackTestingReq' # 策略回测请求，收到后会分成几个周期并行运行
    stockStrategyBackTestingAck = 'eStockStrategyBackTestingAck' # 每个策略会被分成几个周期并行运行，一个周期的Ack
    stopStockStrategyBackTestingReq = 'eStopStockStrategyBackTestingReq'

    newStockStrategyBackTestingParam = 'eNewStockStrategyBackTestingParam' # 新建策略的一个回测参数组合
    newStockStrategyBackTestingPeriod = 'eNewStockStrategyBackTestingPeriod' # 新建策略参数组合的一个回测周期

    stockBackTestingStrategyEngineProcessEnd = 'eStockBackTestingStrategyEngineProcessEnd' # 一个股票回测策略引擎处理结束


class DyEvent:
    def __init__(self, type=None):
        self.type = type
        self.data = {}

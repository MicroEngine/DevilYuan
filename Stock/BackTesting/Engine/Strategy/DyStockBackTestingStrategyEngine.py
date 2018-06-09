import itertools
from collections import OrderedDict

from EventEngine.DyEvent import *
from ...DyStockBackTestingCommon import *
from .DyStockBackTestingStrategyEngineProxy import *
from ....Data.Engine.Common.DyStockDataCommonEngine import *
from ....Data.Engine.DyStockMongoDbEngine import *
from DyCommon.DyCommon import *
from ....Common.DyStockCommon import *


class DyStockBackTestingStrategyEngine(object):
    """接收用户发起的策略回测请求，然后根据时间周期拆分到具体的回测引擎来并行回测"""

    # 二者互斥
    paramGroupNbr = 6 # 并行回测多少个参数组合，只对进程模式有效
    periodNbr = 6 # 回测分成多少个周期，只对进程模式有效
    
    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._progress = DyProgress(self._info)

        self._proxyProcess = DyStockBackTestingStrategyEngineProxy(self._eventEngine)
        self._proxyThread = DyStockBackTestingStrategyEngineProxyThread(self._eventEngine)

        self.setThreadMode()

        self._testedStocks = None

        self._registerEvent()

        self._init()

        # For生成代码组合
        errorInfo = DyErrorInfo(eventEngine)
        errorDataEngine = DyStockDataEngine(eventEngine, errorInfo, registerEvent=False)
        self._errorDaysEngine = errorDataEngine.daysEngine

    def _init(self):
        self._strategyCls = None
        self._settings = None

        self._paramGroups = [] # 回测参数组合
        self._tradeDays = None # 回测周期
        self._paramGroupCount = 0 # 回测参数组合计数

        self._runningBackTestingParamGroups = {} # {ParamGroupNo: [period]}, 正在执行的回测参数组合。period is like [startDay, endDay]

        # reset progress
        self._progress.reset()

    def setThreadMode(self):
        """
            设置回测线程模式
        """
        self._proxy = self._proxyThread
        self._periodNbr = 1
        self._paramGroupNbr = 1

    def setProcessMode(self, mode='参数组合'):
        """"
            设置回测进程模式
            @mode: '参数组合' - 参数组合模式，'周期' - 周期模式
        """
        self._proxy = self._proxyProcess

        if mode == '参数组合':
            self._paramGroupNbr = self.paramGroupNbr
            self._periodNbr = 1
        else:
            self._paramGroupNbr = 1
            self._periodNbr = self.periodNbr

    def _stockSelectTestedCodesHandler(self, event):
        self._testedStocks = event.data

    def _convertCodeParamValue(self, value):
        """ 转换代码参数
            格式: {代码: 股票基金;3}, {代码: 股票;3}, {代码: 600066.SH,300034;2}, {代码: 股票}
                  {代码: 上证}, {代码: 深证}, {代码: 创业板}, {代码: 中小板}, {代码: 中小板基金}
                  不支持个股代码和板块混配
                  ';'后面的数值意思是几个代码组合，默认是1
        """
        if ';' in value:
            codes, combinationNbr = value.split(';')
        else:
            codes = value
            combinationNbr = 1

        if '股票' in codes or '基金' in codes or '上证' in codes or '深证' in codes or '创业板' in codes or '中小板' in codes:
            self._errorDaysEngine.loadCodeTable()

            newCodes = []
            if '股票' in codes:
                codes_ = self._errorDaysEngine.stockCodes
                newCodes += list(codes_)
            else:
                if '上证' in codes:
                    codes_ = self._errorDaysEngine.getIndexStockCodes(self._errorDaysEngine.shIndex)
                    newCodes += list(codes_)

                if '深证' in codes:
                    codes_ = self._errorDaysEngine.getIndexStockCodes(self._errorDaysEngine.szIndex)
                    newCodes += list(codes_)

                if '创业板' in codes:
                    codes_ = self._errorDaysEngine.getIndexStockCodes(self._errorDaysEngine.cybIndex)
                    newCodes += list(codes_)

                if '中小板' in codes:
                    codes_ = self._errorDaysEngine.getIndexStockCodes(self._errorDaysEngine.zxbIndex)
                    newCodes += list(codes_)

            if '基金' in codes:
                codes_ = self._errorDaysEngine.stockFunds
                newCodes += list(codes_)

            codes = newCodes
        else:
            codes = codes.split(',')
            codes = DyStockCommon.getDyStockCodes(codes)

        return list(itertools.combinations(codes, combinationNbr))

    def _convertParamValue(self, value):
        """ 转换数值参数，闭合方式 """

        if not isinstance(value, str):
            return [value]

        # get range and step
        range, step = value.split(';')
        start, end = range.split(':')

        value = [start, end, step]

        for i, v in enumerate(value):
            value[i] = DyCommon.toNumber(v)

        start, end, step = value

        # get values with list format
        ret = []
        while start <= end:
            ret.append(start)
            start += step

        if end not in ret:
            ret.append(end)

        return ret

    def _createParamGroups(self, param):
        """
            @param: OrderedDict, {name: value}
                    value format: range;step or value e.g. 1:10;1 or 1
                                  代码参数，主要是对股票组合做回测分析。
                                  格式：{代码: 股票基金;3} 或者 {代码: 股票;3} 或者{代码: 600066,300034;2} 或者{代码: 股票}，';'后面的数值意思是几个代码组合，默认是1
                                  组合后的代码组合格式为：(代码1, 代码2, ...)
        """
        # get combination of each param value
        values = []
        for name, value in param.items():
            if name == '代码':
                values.append(self._convertCodeParamValue(value))
            else:
                values.append(self._convertParamValue(value))

        values = list(itertools.product(*values))

        # get combination with {param: value}
        names = list(param)
        for value in values:
            group = OrderedDict()
            for key, v in zip(names, value):
                group[key] = v

            self._paramGroups.append(group)

    def _backTestingParamGroups(self):
        """
            类似于窗口推进方式回测参数组合
        """
        if not (self._paramGroups or self._runningBackTestingParamGroups):
            self._eventEngine.put(DyEvent(DyEventType.finish))
            return True

        while len(self._runningBackTestingParamGroups) < self._paramGroupNbr:
            if not self._paramGroups:
                break

            self._paramGroupCount += 1

            self._info.print("开始回测策略: {0}, 参数组合: {1}...".format(self._strategyCls.chName, self._paramGroupCount), DyLogData.ind)

            """ 开始一个参数组合的回测 """
            # pop one param group
            param = self._paramGroups.pop(0)

            # it's one new running paramGroup
            self._runningBackTestingParamGroups[self._paramGroupCount] = []

            # notify Ui to create new param group widget for strategy
            event = DyEvent(DyEventType.newStockStrategyBackTestingParam)
            event.data['class'] = self._strategyCls
            event.data['param'] = {'groupNo': self._paramGroupCount, 'data': param}

            self._eventEngine.put(event)

            """ 开始一个参数组合的多个周期回测 """
            # 分成@self._periodNbr个周期，通过子进程并行运行
            stepSize = (len(self._tradeDays) + self._periodNbr - 1)//self._periodNbr
            if stepSize == 0: return False

            for i in range(0, len(self._tradeDays), stepSize):
                # period
                tradeDays_ = self._tradeDays[i:i + stepSize]

                # notify Ui to create new period widget for strategy
                event = DyEvent(DyEventType.newStockStrategyBackTestingPeriod)
                event.data['class'] = self._strategyCls
                event.data['paramGroupNo'] = self._paramGroupCount
                event.data['period'] = [tradeDays_[0], tradeDays_[-1]]

                self._eventEngine.put(event)

                sleep(1) # !!!sleep so that UI windows can be created firstly.

                # it's one new running period for one new paramGroup
                self._runningBackTestingParamGroups[self._paramGroupCount].append(event.data['period'])

                # create subprocess for processing each period
                reqData = DyStockBackTestingStrategyReqData(self._strategyCls, tradeDays_, self._settings, param, self._testedStocks, self._paramGroupCount)
                self._proxy.startBackTesting(reqData)

        return True

    def _backTesting(self, reqData):
        # unpack
        strategyCls = reqData.strategyCls
        startDate = reqData.tDays[0]
        endDate = reqData.tDays[-1]
        settings = reqData.settings
        param = reqData.param

        self._info.print("开始回测策略: {0}[{1}, {2}]...".format(strategyCls.chName, startDate, endDate), DyLogData.ind)

        self._init()
        self._strategyCls = strategyCls
        self._settings = settings

        # load code table and trade days table
        commonEngine = DyStockDataCommonEngine(DyStockMongoDbEngine(self._info), None, self._info)
        if not commonEngine.load([startDate, endDate]):
            return False

        # 获取回测周期内的所有交易日
        self._tradeDays = commonEngine.getTradeDays(startDate, endDate)

        # 创建策略参数组合
        self._createParamGroups(param)

        # init total progress
        self._progress.init(len(self._tradeDays)*len(self._paramGroups))

        # 推进回测策略回测参数组合
        return self._backTestingParamGroups()

    def _stockStrategyBackTestingReqHandler(self, event):
        # back testing
        if not self._backTesting(event.data):
            self._eventEngine.put(DyEvent(DyEventType.fail))
    
    def _stockStrategyBackTestingAckHandler(self, event):
        if event.data.isClose: # 收盘Ack Data
            self._progress.update()

    def _stockSelectTestedCodesHandler(self, event):
        self._testedStocks = event.data

    def _stockBackTestingStrategyEngineProcessEndHandler(self, event):
        for paramGroupNo, period in event.data.items():
            self._runningBackTestingParamGroups[paramGroupNo].remove(period)

            if not self._runningBackTestingParamGroups[paramGroupNo]:
                del self._runningBackTestingParamGroups[paramGroupNo]
                self._info.print("策略: {0}, 参数组合: {1}回测完成".format(self._strategyCls.chName, paramGroupNo), DyLogData.ind)

                # 向前推进回测参数组合
                self._backTestingParamGroups()

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockStrategyBackTestingReq, self._stockStrategyBackTestingReqHandler, DyStockBackTestingEventHandType.engine)
        self._eventEngine.register(DyEventType.stockStrategyBackTestingAck, self._stockStrategyBackTestingAckHandler, DyStockBackTestingEventHandType.engine)
        self._eventEngine.register(DyEventType.stockBackTestingStrategyEngineProcessEnd, self._stockBackTestingStrategyEngineProcessEndHandler, DyStockBackTestingEventHandType.engine)
        self._eventEngine.register(DyEventType.stockSelectTestedCodes, self._stockSelectTestedCodesHandler)
        #self._eventEngine.register(DyEventType.stopStockStrategyBackTestingReq, self._stopReqHandler, DyStockBackTestingEventHandType.engine)



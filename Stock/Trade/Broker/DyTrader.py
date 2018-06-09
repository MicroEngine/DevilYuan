import os
from time import sleep
import copy
import subprocess
import json

from DyCommon.DyCommon import *
from ..DyStockTradeCommon import *


class DyTrader(object):
    """
        券商交易接口基类
    """
    name = None

    heartBeatTimer = 60
    pollingCurEntrustTimer = 1
    maxRetryNbr = 3 # 最大重试次数


    def __init__(self, eventEngine, info, configFile=None, accountConfigFile=None):
        self._eventEngine = eventEngine
        self._info = info

        # 载入券商的配置文件
        self.__readConfig(configFile, accountConfigFile)
        self._tradePrefix = None if self._config is None else self._config.get('prefix')

    def _file2dict(self, file):
        with open(file) as f:
            return json.load(f)

    def _curInit(self):
        self._curDay = datetime.now().strftime("%Y-%m-%d")

        # 当日委托，用于比较是否有委托状态更新
        self._curEntrusts = None

        # 保存的资金和持仓数据
        # 避免实时从券商接口获取
        self._balance = None
        self._positions = None

        self._exchangeDatetime = None # 最新交易所的时间，来自于监控到的指数更新的最新datetime. Currently, not used!!!

        self._isRegisterStockMarketTicks = False

    def _preLogin(self):
        pass

    def _postLogout(self):
        pass

    def login(self):
        """ 登录 """
        self._info.print('开始登陆[{}]{}交易接口...'.format(self.brokerName, self.name), DyLogData.ind)
        
        # 初始化
        self._curInit()

        self._preLogin()

        # login
        while True:
            try:
                if self._login():
                    break
            except Exception as ex:
                self._info.print('[{}]{}交易接口登陆异常: {}'.format(self.brokerName, self.name, str(ex)), DyLogData.warning)

        self._registerEvent()

        self._info.print('[{}]{}交易接口登陆成功'.format(self.brokerName, self.name), DyLogData.ind)

    def logout(self, oneKeyHangUp=False):
        """ 退出登录 """

        # 注销事件
        self._unregisterEvent()

        self._info.print('开始退出[{}]{}交易接口...'.format(self.brokerName, self.name), DyLogData.ind)

        logoutSucess = self._logout(oneKeyHangUp)

        if logoutSucess:
            self._info.print('[{}]{}交易接口退出成功'.format(self.brokerName, self.name), DyLogData.ind)
        else:
            self._info.print('[{}]{}交易接口退出失败'.format(self.brokerName, self.name), DyLogData.error)

        self._postLogout()

    def _sendHeartBeat(self, event):
        """
            每隔@self.heartBeatTimer秒查询指定接口保持 token 的有效性
        """
        x, y = self.getBalance(parse=False)
        if x is None:
            self._info.print('{}: 心跳失败'.format(self.brokerName), DyLogData.warning)

    def __readConfig(self, configFile, accountConfigFile):
        """ 读取 config """
        self._config = None if configFile is None else self._file2dict(configFile)
        self._accountConfig = None if accountConfigFile is None else self._file2dict(accountConfigFile)

    def _recognizeVerifyCode(self, imagePath, broker):
        """
            识别验证码，返回识别后的字符串，使用 tesseract 实现
            @imagePath: 图片路径
            @broker: 券商
            @return: recognized verify code string
        """
        # 优先JAVA程序识别
        if broker in ['ht', 'yjb', 'gtja']:
            verifyCodeTool = 'getcode_jdk1.5.jar' if broker in ['ht', 'gtja'] else 'yjb_verify_code.jar guojin'
            # 检查 java 环境，若有则调用 jar 包处理
            output = subprocess.getoutput('java -version')

            if 'java version' not in output:
                self._info.print("No JRE installed!", DyLogData.warning)
            else:
                output = subprocess.getoutput(
                        'java -jar %s %s' % (
                            os.path.join(os.path.dirname(__file__), 'ThirdLibrary', verifyCodeTool), imagePath))

                ncodeStart = output.find('code=')
                if ncodeStart == -1: return ""

                return output[ncodeStart + len('code='):]

        # 调用 tesseract 识别
        # ubuntu 15.10 无法识别的手动 export TESSDATA_PREFIX
        systemResult = os.system('tesseract {} result -psm 7'.format(imagePath))
        if systemResult != 0:
            os.system(
                    'export TESSDATA_PREFIX="/usr/share/tesseract-ocr/tessdata/"; tesseract {} result -psm 7'.format(
                            imagePath))

        # 获取识别的验证码
        verifyCodeResult = 'result.txt'
        try:
            with open(verifyCodeResult) as f:
                recognizedCode = f.readline()
        except UnicodeDecodeError:
            try:
                with open(verifyCodeResult, encoding='gbk') as f:
                    recognizedCode = f.readline()
            except:
                recognizedCode = ''

        # 移除空格和换行符
        returnIndex = -1
        recognizedCode = recognizedCode.replace(' ', '')[:returnIndex]

        os.remove(verifyCodeResult)

        return recognizedCode

    def _pollCurEntrusts(self, event):
        """
            定时轮询当日委托直到所有委托都是完成状态
        """
        # 从券商GET当日委托
        header, newEntrusts = self.getCurEntrusts()
        if header is None:
            return
        
        # compare state for each entrust
        stateChange, allDone = self._compareEntrusts(self._curEntrusts, newEntrusts)

        # new current entrusts
        self._curEntrusts = newEntrusts

        # 委托状态有更新
        if stateChange:
            self.updateAccount((header, self._curEntrusts))

        # 所有委托都完成了, no need polling any more
        if allDone:
            self._eventEngine.unregisterTimer(self._pollCurEntrusts, DyStockTradeEventHandType.brokerEngine, self.pollingCurEntrustTimer)

    def _registerEvent(self):
        """
            login成功后注册委托事件和心跳事件
        """
        # heart beat timer
        if self.heartBeatTimer > 0:
            self._eventEngine.registerTimer(self._sendHeartBeat, DyStockTradeEventHandType.brokerEngine, self.heartBeatTimer)

        self._eventEngine.register(DyEventType.stockBuy + self.broker, self._stockBuyHandler, DyStockTradeEventHandType.brokerEngine)
        self._eventEngine.register(DyEventType.stockSell + self.broker, self._stockSellHandler, DyStockTradeEventHandType.brokerEngine)
        self._eventEngine.register(DyEventType.stockCancel + self.broker, self._stockCancelHandler, DyStockTradeEventHandType.brokerEngine)

        self._eventEngine.register(DyEventType.stockBrokerRetry + self.broker, self._stockBrokerRetryHandler, DyStockTradeEventHandType.brokerEngine)

    def _unregisterEvent(self):
        # heart beat timer
        self._eventEngine.unregisterTimer(self._sendHeartBeat, DyStockTradeEventHandType.brokerEngine, self.heartBeatTimer)

        self._eventEngine.unregister(DyEventType.stockBuy + self.broker, self._stockBuyHandler, DyStockTradeEventHandType.brokerEngine)
        self._eventEngine.unregister(DyEventType.stockSell + self.broker, self._stockSellHandler, DyStockTradeEventHandType.brokerEngine)

        # 有可能委托轮询timer启动了，注销它
        self._eventEngine.unregisterTimer(self._pollCurEntrusts, DyStockTradeEventHandType.brokerEngine, self.pollingCurEntrustTimer)

        self._eventEngine.unregister(DyEventType.stockBrokerRetry + self.broker, self._stockBrokerRetryHandler, DyStockTradeEventHandType.brokerEngine)

        self._eventEngine.unregister(DyEventType.stockMarketTicks, self._stockMarketTicksHandler, DyStockTradeEventHandType.brokerEngine)

    def _stockBuyHandler(self, event):
        entrust = event.data

        if self.buy(entrust.code, entrust.name, entrust.price, entrust.totalVolume):
            self._postfixEntrustAction()
        else:
            self._discardEntrust(entrust)

            self.updateCapitalPositions()

    def _stockSellHandler(self, event):
        entrust = event.data

        if self.sell(entrust.code, entrust.name, entrust.price, entrust.totalVolume):
            self._postfixEntrustAction()
        else:
            self._discardEntrust(entrust)

            self.updateCapitalPositions()

    def _stockCancelHandler(self, event):
        entrust = event.data

        self.cancel(entrust)

    def _postfixEntrustAction(self):
        """
            响应委托事件的后续操作
        """
        # 从券商GET资金状况, 主要是为了及时更新账户的资金信息
        self.updateCapital()

        # 启动当日委托状态轮询
        self._eventEngine.registerTimer(self._pollCurEntrusts, DyStockTradeEventHandType.brokerEngine, self.pollingCurEntrustTimer)

    def updateAccount(self, curEntrusts=None):
        """
            从券商更新整个账户状况: 当日委托，当日成交，资金，持仓。
            由于账户管理类是根据委托状态匹配成交，所以委托一定要早于成交更新。
            !!!updating sequence is very tricky.
            @curEntrusts: (header, rows), which is got from broker
        """
        # 当日委托
        self.updateCurEntrusts(curEntrusts)

        # 当日成交
        self.updateCurDeals()

        # 资金状况和持仓
        self.updateCapitalPositions()

    def updateCurDeals(self):
        # 当日成交
        header, rows= self.getCurDeals()
        if header is None:
            self._putBrokerRetryEvent(self.updateCurDeals)
            return

        event = DyEvent(DyEventType.stockCurDealsUpdate + self.broker)
        event.data['header'] = header
        event.data['rows'] = rows

        self._eventEngine.put(event)

    def updateCurEntrusts(self, curEntrusts=None):
        """
            @curEntrusts: (header, rows), which is got from broker
        """
        # 当日委托
        if curEntrusts is None:
            header, curEntrusts= self.getCurEntrusts()
        else:
            header, curEntrusts = curEntrusts

        if header is None:
            self._putBrokerRetryEvent(self.updateCurEntrusts)
            return

        event = DyEvent(DyEventType.stockCurEntrustsUpdate + self.broker)
        event.data['header'] = header
        event.data['rows'] = curEntrusts

        self._eventEngine.put(event)

    def syncPos(self):
        """
            券商接口首次登陆时，必须要调用此接口完成券商接口账户和账户管理类的持仓同步，
            以获取持仓复权因子和成本价。
        """
        # 持仓
        header = None
        while header is None: # 直到成功
            header, rows, autoForegroundHeaderName = self.getPositions(fromBroker=True)

        event = DyEvent(DyEventType.stockPosSyncFromBroker + self.broker)
        event.data['header'] = header
        event.data['rows'] = rows
        event.data['autoForegroundHeaderName'] = autoForegroundHeaderName

        self._eventEngine.put(event)

        self._registerStockMarketTicksEvent(rows)

    def _registerStockMarketTicksEvent(self, positions):
        """
            只监控市场行情事件，但不推送给市场引擎要获取的股票代码。这个由对应的账管理类来完成。
            这样只是时间有点延迟。
            @positions: [[x, x, x, ...]] or [] means no position
        """
        # 如果有持仓，则注册@stockMarketTicks事件
        if positions:
            if not self._isRegisterStockMarketTicks:
                self._eventEngine.register(DyEventType.stockMarketTicks, self._stockMarketTicksHandler, DyStockTradeEventHandType.brokerEngine)
                self._isRegisterStockMarketTicks = True
        else:
            if self._isRegisterStockMarketTicks:
                self._eventEngine.unregister(DyEventType.stockMarketTicks, self._stockMarketTicksHandler, DyStockTradeEventHandType.brokerEngine)
                self._isRegisterStockMarketTicks = False

    def updatePositions(self, fromBroker=True):
        """
            @fromBroker: True - 从券商接口获取持仓数据，False - 从本地获取，本地持仓会根据行情推送的数据进行更新，比从券商获取效率高。
        """
        # 持仓
        header, rows, autoForegroundHeaderName = self.getPositions(fromBroker=fromBroker)
        if header is None:
            self._putBrokerRetryEvent(self.updatePositions)
            return

        event = DyEvent(DyEventType.stockPositionUpdate + self.broker)
        event.data['header'] = header
        event.data['rows'] = rows
        event.data['autoForegroundHeaderName'] = autoForegroundHeaderName

        self._eventEngine.put(event)

        self._registerStockMarketTicksEvent(rows)

    def updateCapitalPositions(self, fromBroker=True):
        # 资金状况
        self.updateCapital(fromBroker)

        # 持仓
        self.updatePositions(fromBroker)

    def updateCapital(self, fromBroker=True):
        header, rows = self.getBalance(fromBroker=fromBroker)
        if header is None:
            self._putBrokerRetryEvent(self.updateCapital)
            return

        event = DyEvent(DyEventType.stockCapitalUpdate + self.broker)
        event.data['header'] = header
        event.data['rows'] = rows

        self._eventEngine.put(event)

    def _putBrokerRetryEvent(self, func):
        event = DyEvent(DyEventType.stockBrokerRetry + self.broker)
        event.data['func'] = func

        self._eventEngine.put(event)

    def _discardEntrust(self, entrust):
        entrust = copy.copy(entrust)
        entrust.status = DyStockEntrust.Status.discarded

        event = DyEvent(DyEventType.stockEntrustUpdate + self.broker)
        event.data = entrust

        self._eventEngine.put(event)

    def _stockBrokerRetryHandler(self, event):
        func = event.data['func']

        self._info.print('{}: 重试{}...'.format(self.brokerName, func.__name__), DyLogData.warning)
        sleep(1)
        func()

    def __isValidTicks(self, ticks):
        """
            是否是有效的Ticks
            @return: bool
        """
        if not DyStockTradeCommon.enableCtaEngineTickOptimization:
            return True

        szIndexTick = ticks.get(DyStockCommon.szIndex)
        if szIndexTick is None:
            return False

        if szIndexTick.date != self._curDay:
            return False

        # 确保现在是有效交易时间
        if not '09:25:00' <= szIndexTick.time < '15:00:10':
            return False

        return True

    def __setExchangeDatetime(self, ticks):
        szIndexTick = ticks.get(DyStockCommon.szIndex)
        shIndexTick = ticks.get(DyStockCommon.shIndex)

        if szIndexTick is not None and shIndextick is not None:
            self._exchangeDatetime = max(szIndexTick.datetime, shIndexTick.datetime)
        elif szIndexTick is not None:
            self._exchangeDatetime = szIndexTick.datetime
        elif shIndexTick is not None:
            self._exchangeDatetime = shIndexTick.datetime

    def _stockMarketTicksHandler(self, event):
        """
            市场行情处理
        """
        # unpack
        ticks = event.data

        # 设置交易所的最新时间
        #self.__setExchangeDatetime(ticks)

        # call virtual @onTicks of instance
        if not self.__isValidTicks(ticks):
            return

        self.onTicks(ticks)

        # update from local tickly for UI
        # capital
        header, rows = self.getBalance(fromBroker=False)
        if header is not None:
            event = DyEvent(DyEventType.stockCapitalTickUpdate + self.broker)
            event.data['header'] = header
            event.data['rows'] = rows

            self._eventEngine.put(event)

        # positions
        header, rows, autoForegroundHeaderName = self.getPositions(fromBroker=False)
        if header is not None:
            event = DyEvent(DyEventType.stockPositionTickUpdate + self.broker)
            event.data['header'] = header
            event.data['rows'] = rows
            event.data['autoForegroundHeaderName'] = autoForegroundHeaderName

            self._eventEngine.put(event)

    def onTicks(self, ticks):
        """
            由子类重载来更新实时持仓和账户信息
        """
        pass

    def retryWrapper(func):
        """
            券商接口的重试装饰器
            装饰跟券商网络相关的接口
        """
        def wrapper(self, *args, **kwargs):
            for _ in range(self.maxRetryNbr):
                x = func(self, *args, **kwargs)

                if isinstance(x, tuple):
                    if x[0] is not None:
                        return x
                else:
                    if x is not None and x is not False:
                        return x

            self._info.print('{}: {}失败{}次'.format(self.brokerName, func.__name__, self.maxRetryNbr), DyLogData.error)
            return x

        return wrapper

    def _getEntrustState(self, entrustNo, entrusts):
        for entrust in entrusts:
            if entrust[self.curEntrustHeaderNoIndex] == entrustNo:
                return entrust[self.curEntrustHeaderStateIndex]

        return None

    def _setCurEntrustHeaderIndex(self):
        if self.curEntrustHeaderNoIndex is not None:
            return

        self.curEntrustHeaderNoIndex = self.curEntrustHeader.index(self.curEntrustHeaderNo)
        self.curEntrustHeaderStateIndex = self.curEntrustHeader.index(self.curEntrustHeaderState)

    def _compareEntrusts(self, entrusts, newEntrusts):
        """
            比较两组委托的状态
            虚函数，由基类调用
            @entrusts: old entrusts
            @newEntrusts: new entrusts
            @return: 委托状态变化，所有委托都完成
        """
        # 没有新的委托
        if newEntrusts is None:
            return False, False

        # 没有老委托，则是刚开始查询委托
        if entrusts is None:
            stateChange = True
            allDone = True

            entrusts = newEntrusts

        else:
            stateChange = False
            allDone = True

        # 设置index
        self._setCurEntrustHeaderIndex()

        # compare state for each new entrust
        for newEntrust in newEntrusts:
            newEntrustNo = newEntrust[self.curEntrustHeaderNoIndex]
            newEntrustState = newEntrust[self.curEntrustHeaderStateIndex]

            entrustState = self._getEntrustState(newEntrustNo, entrusts)

            if entrustState != newEntrustState:
                stateChange = True

            if newEntrustState not in ['已成', '已撤', '废单', '部撤']:
                allDone = False

        return stateChange, allDone

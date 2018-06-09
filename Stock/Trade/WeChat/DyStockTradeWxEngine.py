import threading
import requests

from .wxbot import WXBot

from DyCommon.DyCommon import *
from EventEngine.DyEvent import *
from ..DyStockTradeCommon import *


class DyStockTradeWxBot(WXBot):
    def __init__(self, eventEngine, info):
        super().__init__()

        self._eventEngine = eventEngine
        self._info = info

        self.DEBUG = False

    def handle_msg_all(self, msg):
        if msg['user']['name'] == 'self':

            event = DyEvent(DyEventType.wxQueryStockStrategy)
            event.data = msg['content']['data']

            self._eventEngine.put(event)

    def send(self, msg):
        self.send_msg_by_uid(msg, self.my_account['UserName'])


class DyStockTradeWxEngine(object):
    """
        使用WXBot进行实盘策略信号提醒
    """
    scKey = None


    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._wxBot = None
        self._isStop = True

        self._latestStrategyData = {} # {strategy name: (strategy class, time, data)}
        self._latestMarketStrengthData = None

        self._pushAction = None # 发给WX的Action

        self._registerEvent()

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.startStockCtaStrategy, self._startStockCtaStrategyHandler, DyStockTradeEventHandType.wxEngine)
        self._eventEngine.register(DyEventType.stopStockCtaStrategy, self._stopStockCtaStrategyHandler, DyStockTradeEventHandType.wxEngine)

        self._eventEngine.register(DyEventType.startStockWx, self._startStockWxHandler, DyStockTradeEventHandType.wxEngine)
        self._eventEngine.register(DyEventType.stopStockWx, self._stopStockWxHandler, DyStockTradeEventHandType.wxEngine)

        self._eventEngine.register(DyEventType.wxQueryStockStrategy, self._wxQueryStockStrategyHandler, DyStockTradeEventHandType.wxEngine)
        self._eventEngine.register(DyEventType.sendStockTestWx, self._sendStockTestWxHandler, DyStockTradeEventHandType.wxEngine)

        self._eventEngine.register(DyEventType.stockMarketStrengthUpdateFromUi, self._stockMarketStrengthUpdateFromUiHandler, DyStockTradeEventHandType.wxEngine)

        self._eventEngine.register(DyEventType.stockStrategyOnOpen, self._stockStrategyOnOpenHandler, DyStockTradeEventHandType.wxEngine)

    def _startStockCtaStrategyHandler(self, event):
        strategyCls = event.data['class']

        self._eventEngine.register(DyEventType.stockMarketMonitorUi + strategyCls.name, self._stockMarketMonitorUiHandler, DyStockTradeEventHandType.wxEngine)

        self._latestStrategyData[strategyCls.name] = None
        
    def _stopStockCtaStrategyHandler(self, event):
        strategyCls = event.data['class']

        self._eventEngine.unregister(DyEventType.stockMarketMonitorUi + strategyCls.name, self._stockMarketMonitorUiHandler, DyStockTradeEventHandType.wxEngine)

        del self._latestStrategyData[strategyCls.name]

    def _startWxBot(self):
        """
            全新开始一个WXBot
        """
        self._wxBotThread = threading.Thread(target=self._wxBotThreadHandler, args=(self._eventEngine, self._info))
        self._wxBotThread.start()

    def _startStockWxHandler(self, event):
        self._isStop = False

        if self._wxBot is not None:
            return

        self._startWxBot()

    def _wxBotThreadHandler(self, eventEngine, info):
        self._wxBot = DyStockTradeWxBot(eventEngine, info)

        self._wxBot.run()
                    
    def _stopStockWxHandler(self, event):
        self._isStop = True

    def _sendWx(self, msg):
        """
            向自己发送微信
        """
        self._wxBot.send(msg)

    def _send(self, strategyCls, time, name, data, isMsgList=False, pureMsg=False):
        """
            @time: 本地时间
            @name: @data的名字
            @data: [[x, y]] or [WX message]
            @isMsgList: @data format is list of WX message(string)
        """
        if pureMsg:
            text = '{0}[{1}]:\n{2}-{3}'.format(strategyCls.chName, time.strftime('%H:%M:%S'), name, data)

            # sent to WX
            self._sendWx(text)
        else:
            if isMsgList:
                # send header
                text = '{0}[{1}]:\n{2}-'.format(strategyCls.chName, time.strftime('%H:%M:%S'), name)
                self._sendWx(text)

                # send body
                for text in data:
                    self._sendWx(text)

            else:
                # 只显示两位小数
                newData = []
                for row in data:
                    newData.append([float('%.2f'%x) if isinstance(x, float) else x for x in row])

                text = '{0}[{1}]:\n{2}-{3}'.format(strategyCls.chName, time.strftime('%H:%M:%S'), name, newData)

                # sent to WX
                self._sendWx(text)

    def _sendWxViaFt(self, title, msg):
        """
            通过server酱（方糖）推送
        """
        if not self.scKey:
            return

        data = {'text': title,
                'desp': msg
                }
        requests.post('http://sc.ftqq.com/{}.send'.format(self.scKey), data=data)

    def _sendViaFt(self, strategyCls, time, name, data, isMsgList=False, pureMsg=False):
        """
            通过server酱（方糖）推送
            @time: 本地时间
            @name: @data的名字
            @data: [[x, y]] or [WX message]
            @isMsgList: @data format is list of WX message(string)
        """
        if pureMsg:
            text = '{0}[{1}]:\n{2}-{3}'.format(strategyCls.chName, time.strftime('%H:%M:%S'), name, data)

            # sent to WX
            self._sendWxViaFt(strategyCls.chName, text)
        else:
            if isMsgList:
                # send header
                text = '{0}[{1}]:\n{2}-'.format(strategyCls.chName, time.strftime('%H:%M:%S'), name)
                self._sendWxViaFt(strategyCls.chName, text)

                # send body
                for text in data:
                    self._sendWxViaFt(strategyCls.chName, text)

            else:
                # 只显示两位小数
                newData = []
                for row in data:
                    newData.append([float('%.2f'%x) if isinstance(x, float) else x for x in row])

                text = '{0}[{1}]:\n{2}-{3}'.format(strategyCls.chName, time.strftime('%H:%M:%S'), name, newData)

                # sent to WX
                self._sendWxViaFt(strategyCls.chName, text)

    def _stockMarketMonitorUiHandler(self, event):
        if self._isStop:
            return

        if self._wxBot is None:
            return

        strategyCls = event.data['class']

        # save strategy latest data
        if 'data' in event.data:
            data = event.data['data']['data']

            if strategyCls.name in self._latestStrategyData:
                self._latestStrategyData[strategyCls.name] = (strategyCls, datetime.now(), '数据', data)

        # check if there's signal or operation of strategy
        if 'ind' in event.data:
            if 'signalDetails' in event.data['ind']:
                signalDetails = event.data['ind']['signalDetails']

                self._send(strategyCls, datetime.now(), '信号明细', signalDetails)
                self._sendViaFt(strategyCls, datetime.now(), '信号明细', signalDetails)

            if 'op' in event.data['ind']:
                op = event.data['ind']['op']

                self._send(strategyCls, datetime.now(), '操作', op)
                self._sendViaFt(strategyCls, datetime.now(), '操作', op)

    def _sendStockTestWxHandler(self, event):
        if self._isStop:
            return

        if self._wxBot is None:
            return

        text = event.data

        # sent to WX
        self._sendWx(text)

    def _stockMarketStrengthUpdateFromUiHandler(self, event):
        """
            处理来自于UI的市场强度更新事件
        """
        self._latestMarketStrengthData = event.data

    def _stockMarketTicksHandler(self, event):
        if self._pushAction is None:
            return

        ticks = event.data

        strategyData = self._latestStrategyData.get('DyST_IndexMeanReversion')
        if strategyData is None:
            return

        strategyCls = strategyData[0]

        tick = ticks.get(strategyCls.targetCode)
        if tick is None:
            return

        # event
        event = DyEvent(DyEventType.stockStrategyManualBuy)
        event.data['class'] = strategyCls
        event.data['tick'] = tick
        event.data['volume'] = 100

        event.data['price'] = round(tick.preClose * 0.92, 3)

        self._eventEngine.put(event)

        self._info.print('通过WX委托买入{0}, {1}股, 价格{2}'.format(tick.name, event.data['volume'], event.data['price']), DyLogData.ind1)

        # sent to WX
        self._sendWx('委托买入{0}, {1}股, 价格{2}'.format(tick.name, event.data['volume'], event.data['price']))

        # clear
        self._pushAction = None
        self._eventEngine.unregister(DyEventType.stockMarketTicks, self._stockMarketTicksHandler, DyStockTradeEventHandType.wxEngine)

    def _queryMarketStrength(self):
        if self._latestMarketStrengthData is None:
            return

        # assemble to text
        text = ''
        for name, value in self._latestMarketStrengthData:
            if text:
                text += '\n'

            text += '{0}: {1}'.format(name, '' if value is None else value)

        # sent to WX
        self._sendWx(text)

    def _queryStrategyData(self):
        for _, group in self._latestStrategyData.items():
            if group is None:
                continue

            strategyCls, time, name, data = group
            if not strategyCls.enableQuery:
                continue

            if hasattr(strategyCls, 'data2Msg'):
                isMsgList = True
                data = strategyCls.data2Msg(data)
            else:
                isMsgList = False
                data = [data[-1]]

            self._send(strategyCls, time, name, data, isMsgList)

    def _wxQueryStockStrategyHandler(self, event):
        """
            WX远程请求市场和策略相关的数据
            @message: 1, 2, 3
        """
        if self._isStop:
            return

        if self._wxBot is None:
            return

        message = event.data

        if message == '1': # 策略行情数据
            self._queryStrategyData()
        
        elif message == '2': # 市场强度
            self._queryMarketStrength()

        elif message == '3': # 测试用，买入指数均值回归策略的标的
            self._pushAction = '买入'
            self._eventEngine.register(DyEventType.stockMarketTicks, self._stockMarketTicksHandler, DyStockTradeEventHandType.wxEngine)

    def _stockStrategyOnOpenHandler(self, event):
        if self._isStop:
            return

        if self._wxBot is None:
            return

        strategyCls = event.data['class']
        msg = event.data['msg']

        self._send(strategyCls, datetime.now(), 'OnOpen', msg, pureMsg=True)
        self._sendViaFt(strategyCls, datetime.now(), 'OnOpen', msg, pureMsg=True)

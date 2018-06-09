from datetime import datetime
from time import sleep
import threading

import tushare as ts

from EventEngine.DyEvent import *
from DyCommon.DyCommon import *
from DyCommon.DyScheduler import DyScheduler


class DyStockTradeOneKeyHangUp(object):
    """
        股票交易一键挂机
        用户必须先启动好策略，然后才能一键挂机。
    """
    testMode = False
    testModeInterval = 60 # 单位秒


    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._scheduler = None
        self._tradeDays = {}

    def _checkDay(self):
        """
            check current day is trade day or not
            @return: bool,
                     None - error
        """
        curDay = datetime.now().strftime("%Y-%m-%d")

        # set trade days by data gotten from TuShare
        if curDay not in self._tradeDays:
            for _ in range(3):
                if self._setTradeDays(curDay):
                    break

                sleep(1)

        isTradeDay = self._tradeDays.get(curDay)
        if isTradeDay is None:
            self._info.print("一键挂机: TuShare缺失{}交易日数据".format(curDay), DyLogData.error)
           
        return isTradeDay

    def _beginDay(self):
        if self._checkDay() or self.testMode:
            self._eventEngine.put(DyEvent(DyEventType.beginStockTradeDay))

    def _endDay(self):
        if self._checkDay() or self.testMode:
            self._eventEngine.put(DyEvent(DyEventType.endStockTradeDay))

    def _setTradeDays(self, startDate):
        try:
            df = ts.trade_cal()

            df = df.set_index('calendarDate')
            df = df[startDate:]

            # get trade days
            dates = DyTime.getDates(startDate, df.index[-1], strFormat=True)
            self._tradeDays = {}
            for date in dates:
                if df.ix[date, 'isOpen'] == 1:
                    self._tradeDays[date] = True
                else:
                    self._tradeDays[date] = False

        except Exception as ex:
            self._info.print("一键挂机: 从TuShare获取交易日[{}]数据异常: {}".format(startDate, str(ex)), DyLogData.warning)
            return False

        return True

    def _testModeRun(self):
        while True:
            sleep(self.testModeInterval)
            self._beginDay()

            sleep(self.testModeInterval)
            self._endDay()

    def start(self):
        assert self._scheduler is None

        isTradeDay = self._checkDay()
        if isTradeDay is None:
            return False

        # 推送endTradeDay事件
        if not isTradeDay or datetime.now().strftime('%H:%M:%S') > '15:45:00':
            self._eventEngine.put(DyEvent(DyEventType.endStockTradeDay))

        if self.testMode:
            threading.Thread(target=self._testModeRun).start()
        else:
            self._scheduler = DyScheduler()

            self._scheduler.addJob(self._beginDay, {1, 2, 3, 4, 5}, '08:30:00')
            self._scheduler.addJob(self._endDay, {1, 2, 3, 4, 5}, '15:45:00')

            self._scheduler.start()

        return True

    def stop(self):
        if self._scheduler is None:
            return

        self._scheduler.shutdown()
        self._scheduler = None


import os
import functools
import time as DySysTime
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import json
import numpy as np

from EventEngine.DyEvent import *


class DyLogData:
    error = '错误'
    warning = '警告'
    info = '信息'
    ind = '通知' # indication
    ind1 = '通知1'
    ind2 = '通知2'

    def __init__(self, description, type):
        self.time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-4]
        self.type = type
        self.description = description


class DyInfo(object):

    def __init__(self, eventEngine):
        self._eventEngine = eventEngine

        self._progressSingle = 0
        self._progressTotal = 0

    def print(self, description, type=DyLogData.info):
        event = DyEvent(DyEventType.log)
        event.data = DyLogData(description, type)

        self._eventEngine.put(event)

    def progressSingle(self, percent):
        if self._progressSingle != percent:
            self._progressSingle = percent

            event = DyEvent(DyEventType.progressSingle)
            event.data = percent

            self._eventEngine.put(event)

    def progressTotal(self, percent):
        if self._progressTotal != percent:
            self._progressTotal = percent

            event = DyEvent(DyEventType.progressTotal)
            event.data = percent

            self._eventEngine.put(event)

    def initProgress(self):
        self.progressSingle(0)
        self.progressTotal(0)


class DyErrorInfo(object):
    """ 只打印错误和警告信息 """

    def __init__(self, eventEngine):
        self._eventEngine = eventEngine

    def print(self, description, type=DyLogData.info):
        if type == DyLogData.error or type == DyLogData.warning:
            event = DyEvent(DyEventType.log)
            event.data = DyLogData(description, type)

            self._eventEngine.put(event)

    def progressSingle(self, percent):
        pass

    def progressTotal(self, percent):
        pass

    def initProgress(self):
        pass


class DyErrorProgressInfo(DyInfo):
    """ 只打印错误和警告信息，及进度条显示 """

    def __init__(self, eventEngine):
        super().__init__(eventEngine)

    def print(self, description, type=DyLogData.info):
        if type == DyLogData.error or type == DyLogData.warning:
            event = DyEvent(DyEventType.log)
            event.data = DyLogData(description, type)

            self._eventEngine.put(event)


class DyQueueInfo:

    def __init__(self, outQueue):
        self._outQueue = outQueue

    def print(self, description, type=DyLogData.info):
        if type == DyLogData.error or type == DyLogData.warning:
            event = DyEvent(DyEventType.log)
            event.data = DyLogData(description, type)

            self._outQueue.put(event)

    def progressSingle(self, percent):
        pass

    def progressTotal(self, percent):
        pass

    def initProgress(self):
        pass


class DyDummyInfo:

    def __init__(self):
        pass

    def print(self, description, type=DyLogData.info):
        pass

    def progressSingle(self, percent):
        pass

    def progressTotal(self, percent):
        pass

    def initProgress(self):
        pass


class DySubInfo:

    def __init__(self, paramGroupNo, period, outQueue):
        """
            @paramGroupNo: 策略参数组合
            @period: 策略参数组合的一个周期，[start date, end date]
        """
        self._paramGroupNo = paramGroupNo
        self._period = period
        self._outQueue = outQueue

        self._progressTotal = 0

        self._enabled = True

    def print(self, description, type=DyLogData.info):
        if not self._enabled and type != DyLogData.error and type != DyLogData.warning: return

        event = DyEvent(DyEventType.subLog_ + '_' + str(self._paramGroupNo) + str(self._period))
        event.data = DyLogData(description, type)

        self._outQueue.put(event)

    def progressSingle(self, percent):
        pass

    def progressTotal(self, percent):
        if not self._enabled: return

        if self._progressTotal != percent:
            self._progressTotal = percent

            event = DyEvent(DyEventType.subProgressTotal_ + '_' + str(self._paramGroupNo) + str(self._period))
            event.data = percent

            self._outQueue.put(event)

    def initProgress(self):
        self.progressTotal(0)

    def enable(self, enable=True):
        self._enabled = enable


class DyTime:

    def getTimeInterval(time1, time2):
        """
            获取时间差，单位是秒
            @time: 'hh:mm:ss'
        """
        time1S = int(time1[:2])*3600 + int(time1[3:5])*60 + int(time1[-2:])
        time2S = int(time2[:2])*3600 + int(time2[3:5])*60 + int(time2[-2:])

        return time2S - time1S

    def getDate(start, step):
        if isinstance(start, str):
            start = start.split('-')
            start = datetime( int(start[0]), int(start[1]), int(start[2]) )

        start += timedelta(days=step)

        return start

    def getDateStr(start, step):
        if isinstance(start, str):
            start = start.split('-')
            start = datetime( int(start[0]), int(start[1]), int(start[2]) )

        start += timedelta(days=step)

        return start.strftime("%Y-%m-%d")

    def dateCmp(date1, date2):
        if isinstance(date1, str):
            date1 = date1.split('-')
        if isinstance(date1, list):
            date1 = datetime( int(date1[0]), int(date1[1]), int(date1[2]) )
        if isinstance(date1, datetime):
            date1 = datetime(date1.year, date1.month, date1.day)

        if isinstance(date2, str):
            date2 = date2.split('-')
        if isinstance(date2, list):
            date2 = datetime( int(date2[0]), int(date2[1]), int(date2[2]) )
        if isinstance(date2, datetime):
            date2 = datetime(date2.year, date2.month, date2.day)

        if date1 > date2: return 1
        elif date1 == date2: return 0
        else: return -1


    def isDateFormatCorrect(date):
        if not isinstance(date, str): return False

        date = date.split('-')

        if len(date) != 3: return False

        if len(date[0]) != 4 or len(date[1]) != 2 or len(date[2]) != 2: return False

        for part in date:
            for c in part:
                if c not in ['0','1','2','3','4','5','6','7','8','9']:
                    return False

        # year
        if int(date[0][0]) not in range(1, 10): return False
        if int(date[0][1]) not in range(0, 10): return False
        if int(date[0][2]) not in range(0, 10): return False
        if int(date[0][3]) not in range(0, 10): return False

        # month
        if int(date[1]) not in range(1, 13): return False
        # day
        if int(date[2]) not in range(1, 32): return False

        return True


    def getDates(start, end, strFormat=False):
        if isinstance(start, str):
            start = start.split('-')
            start = datetime( int(start[0]), int(start[1]), int(start[2]) )

        if isinstance(end, str):
            end = end.split('-')
            end = datetime( int(end[0]), int(end[1]), int(end[2]) )


        dates = []

        i = timedelta(days=0)
        while i <= end - start:
            dates.append((start + i).strftime("%Y-%m-%d") if strFormat else (start + i))
            i += timedelta(days=1)

        return dates

    def isInMonths(year, month, months):
        """ @months: {year:{month:None}} """

        if year not in months: return False
        if month not in months[year]: return False

        return True

    def getMonths(start, end):
        """ @return: {year:{month:None}} """

        if start == None or end == None: return None

        dates = StockTime.GetDates(start, end)

        months = {}

        for date in dates:
            date = date.strftime("%Y-%m").split('-')

            if date[0] not in months:
                months[date[0]] = {}

            months[date[0]][date[1]] = None

        return months

    def getNextMonth(date):
        date = date.split('-')
        
        month = int(date[1])
        
        day = '01'

        if month == 12:
            year = str(int(date[0]) + 1)
            month = '01'
        else:
            year = date[0]
            month = str(month + 1)
            if len(month) == 1: month = '0' + month
             
        date = year + '-' + month + '-' + day
        return date

    def getPreMonth(date):
        date = date.split('-')
        
        month = int(date[1])
        
        day = '01'

        if month == 1:
            year = str(int(date[0]) - 1)
            month = '12'
        else:
            year = date[0]
            month = str(month - 1)
            if len(month) == 1: month = '0' + month
             
        date = year + '-' + month + '-' + day
        return date

    def instanceTimeitWrapper(func):
        """
            实例成员函数的耗时统计的装饰器
        """
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            start = DySysTime.time()

            func(self, *args, **kwargs)

            end = DySysTime.time()
            print('{}: {}耗时{}ms'.format(self.__class__.__name__, func.__name__, round((end - start)*1000, 3)))

        return wrapper


class DyMatplotlib:
    """ 管理matplotlib的figure的分配 """

    curFigNums = []
    figNbr = 8

    def newFig():
        figs = plt.get_fignums()

        for fig in range(1, DyMatplotlib.figNbr + 1):
            if fig not in figs:
                plt.figure(fig)
                DyMatplotlib.curFigNums.append(fig)
                return

        fig = DyMatplotlib.curFigNums[0]
        plt.close(fig)
        plt.figure(fig)

        del DyMatplotlib.curFigNums[0]
        DyMatplotlib.curFigNums.append(fig)


class DyProgress(object):

    def __init__(self, info):
        self._info = info

        # Ui progress related
        self._totalReqNbr = 0
        self._singleReqNbr = 0

        self._totalReqCount = 0 # decreased count
        self._singleReqCount = 0 # decreased count

    def init(self, totalReqNbr, singleUpdateUiStep=1, totalUpdateUiStep=1):
        """
            @singleUpdateUiStep: each @singleUpdateUiStep percent update single progress UI, less updating single progress UI less time latency.
                               Usually it's useful for mass fast computing procedure. Must be between 1 ~ 100.
            @totalUpdateUiStep: each @totalUpdateUiStep percent update total progress UI. Must be between 1 ~ 100.
        """
        self._totalReqNbr = totalReqNbr
        self._singleReqNbr = totalReqNbr//100

        self._totalReqCount = totalReqNbr
        self._singleReqCount = self._singleReqNbr

        # init Ui progress
        percent = 100 if self._singleReqCount == 0 else 0
        self._info.progressSingle(percent)

        percent = 100 if self._totalReqCount == 0 else 0
        self._info.progressTotal(percent)

        self._singleUpdateUiStep = singleUpdateUiStep
        self._totalUpdateUiStep = totalUpdateUiStep

    def _updateSingle(self):
        # decrease firstly
        if self._singleReqCount > 0: # in case total request nbr is less than 100
            self._singleReqCount -= 1

        if self._singleReqCount == 0: # if 0, always set 100% without considering single request nbr
            percent = 100
        else: # > 0, which still means @self._singleReqNbr > 0
            percent = (self._singleReqNbr - self._singleReqCount)*100//self._singleReqNbr

        # notify Ui progress
        if percent%self._singleUpdateUiStep == 0 or percent == 100:
            self._info.progressSingle(percent)

        # new start for single progress
        if self._singleReqCount == 0:
            self._singleReqNbr = min(self._totalReqCount, self._singleReqNbr) # for last left request nbr, which must be less than or equal @self._singleReqNbr
            self._singleReqCount = self._singleReqNbr

    def _updateTotal(self):
        # decrease firstly
        if self._totalReqCount > 0: # in case no any request
            self._totalReqCount -= 1

        if self._totalReqCount == 0: # if 0, always set 100% without considering total request nbr
            percent = 100

        else: # > 0, which still means @self._totalReqNbr > 0
            percent = (self._totalReqNbr - self._totalReqCount)*100//self._totalReqNbr

        # notify Ui progress
        if percent%self._totalUpdateUiStep == 0  or percent == 100:
            self._info.progressTotal(percent)

    def update(self):
        # must update total progress firstly because @self._totalReqCount will be used at single progress updating
        self._updateTotal()

        self._updateSingle()

    def reset(self):
        self._info.progressSingle(0)
        self._info.progressTotal(0)

    @property
    def totalReqCount(self):
        return self._totalReqCount


class DyCommon:
    def toNumber(v):
        """
            优先转成int，float，若没法转换，则返回本身值。
        """
        try:
            vi = int(v)
            vf = float(v)

            v = vi if vi == vf else vf # 优先整数
        except:
            try:
                v = float(v)
            except:
                pass

        return v

    def toFloat(value, default=0):
        try:
            value = float(value)
        except Exception as ex:
            value = default

        return value

    def createPath(path):
        """
            @path: like 'Stock/User/Config', use linux format
        """
        parentPath = os.getcwd()
        parentPathList = parentPath.split(os.path.sep)
        parentPath = os.path.sep.join(parentPathList[:-1])

        pathList = path.split('/')
        for path in ['DevilYuanMagicBox'] + pathList:
            parentPath = os.path.join(parentPath, path)
            if not os.path.exists(parentPath):
                os.mkdir(parentPath)

        return parentPath


class DyJsonEncoder(json.JSONEncoder):
    """
       For numpy types serialized to JSON
    """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super().default(obj)


class DyStockBackTestingEventHandType:
    engine = 0
    other = 1

    nbr = 2


class DyStockBackTestingStrategyReqData:
    def __init__(self, strategyCls, tDays, settings, param, codes=None, paramGroupNo=None):
        self.strategyCls = strategyCls
        self.tDays = tDays # 来自UI的req，@tDays是[start date, end date]。分发给子进程的req，@tDays是[tDay]
        self.settings = settings # {}, 回测参数设置, 不包含日期(也就是说忽略日期相关参数)
        self.codes = codes # 测试用的股票代码集
        self.param = param # 策略参数
        self.paramGroupNo = paramGroupNo # 策略参数组合号


class DyStockBackTestingStrategyAckData:
    def __init__(self, datetime, strategyCls, paramGroupNo, period, isClose=False):
        self.datetime = datetime
        self.strategyCls = strategyCls
        self.paramGroupNo = paramGroupNo # 策略参数组合编号
        self.period = period  # 策略运行周期, [start tDay, end tDay]

        self.day = None  # 策略现在运行日期

        self.deals = [] # 交易细节的增量
        self.curPos = [] # 持仓

        self.curCash = None
        self.initCash = None

        self.isClose = isClose # 是不是收盘后的Ack


class DyStockBackTestingCommon:
    maViewerIndicator = 'close'

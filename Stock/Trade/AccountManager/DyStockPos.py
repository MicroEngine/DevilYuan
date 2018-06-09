from ..DyStockTradeCommon import *


class DyStockPos:
    """
        一只股票的持仓，一只股票对应一个实例
        实盘和回测时，行为会有所不同，比如@datetime，@cost，@holdingPeriod，@onOpen()
        !!!一定要注意哪些成员变量是当日有效，哪些是持有期内有效的。
    """


    def __init__(self, datetime, strategyCls, code, name, price, volume, tradeCost=0):
        self.datetime = datetime # 第一次建仓时间，实盘时，datetime则从券商获取，即首单成交时间，类型是string。
                                 # 这个跟回测有区别，回测时类型是datetime。

        self.strategyCls = strategyCls # 第一次建立此头寸的策略类

        self.code = code
        self.name = name
        
        self.totalVolume = volume
        self.availVolume = 0 if DyStockTradeCommon.T1 else volume

        self.high = price # 持有期内最高价格
        self.closeHigh = None # 持有期内收盘最高价格
        self.cost = (price*volume + tradeCost)/volume # 持有期内每股成本价，算上手续费。实盘时，成本会更新成券商账户的持仓成本，由CTA引擎更新。
        self.price = price # 现价

        self.pnlRatio = 0 # 当前盈亏比
        self.maxPnlRatio = 0 # 持有周期内的最大盈利比，回测时有效
        self.minPnlRatio = 0 # 持有周期内的最大亏损比，回测时有效
        self.holdingPeriod = 1 # 持有期（以交易日为单位），实盘时，这个参数收盘后会保存到磁盘，策略开盘载入时会计数。主要是为了止时模块的操作。

        self.xrd = False # 持有期内是否发生除权除息，回测时和策略持仓有效

        self.reserved = None # 持有期内保留字段，可以由策略使用

        self._updatePrice(price)

        self._curInit()

    def _curInit(self):
        """
            初始化当日相关的数据，主要是除复权相关的数据。
        """
        self.preClose = None # 昨日收盘价，回测时有效
        self.sync = False # 主要是除复权导致。若是策略持仓，则是券商账户管理持仓跟策略持仓同步，若是账户管理持仓，则是券商接口账户持仓跟账户管理持仓。

        # 复权因子。分成价格和持仓量的原因是，实盘时，有些股票只除息了，这时成本价格变了，但持仓量不变。
        # 对回测来讲，这两个值一样。
        # 回测时根据当日第一个tick或者bar推算出来。实盘时则由Broker驱动。
        self.priceAdjFactor = None # 当日价格复权因子，
        self.volumeAdjFactor = None # 当日持仓量复权因子

    def _updatePrice(self, price, high=None, low=None):
        """
            更新跟当前价格，最高价，最低价相关的持仓数据。这里假设price，high，low数据没有错误。
            @price: 当前价格
            @high: bar的high
            @low: bar的low
        """
        self.price = price

        if self.cost != 0:
            self.pnlRatio = (self.price - self.cost)/self.cost * 100

            if high is None:
                self.maxPnlRatio = max(self.maxPnlRatio, self.pnlRatio)
            else:
                self.maxPnlRatio = max(self.maxPnlRatio, (high - self.cost)/self.cost * 100)

            if low is None:
                self.minPnlRatio = min(self.minPnlRatio, self.pnlRatio)
            else:
                self.minPnlRatio = min(self.minPnlRatio, (low - self.cost)/self.cost * 100)

        if high is None:
            self.high = max(self.high, price)
        else:
            self.high = max(self.high, high)

    def addPos(self, datetime, strategyCls, price, volume, tradeCost=0):
        #self.datetime = datetime
        #self.strategyCls = strategyCls

        self.cost = (self.cost*self.totalVolume + price*volume + tradeCost)/(self.totalVolume + volume)

        self.totalVolume += volume
        if not DyStockTradeCommon.T1:
            self.availVolume += volume

        self._updatePrice(price)

    def removePos(self, price, volume, tradeCost=0, removeAvailVolume=True):
        """
            Note: !!!cost isn't recalculated, which is different with 炒股软件
        """
        if removeAvailVolume:
            if not self.availVolume >= volume > 0:
                return None, None

            self.availVolume -= volume

        self.totalVolume -= volume
        assert self.totalVolume >= 0

        pnl = (price - self.cost)*volume - tradeCost
        pnlRatio = pnl/(self.cost*volume)*100

        return pnl, pnlRatio

    def onOpen(self, date, dataEngine):
        """
            持仓开盘前的操作。
            回测时有效。由于实盘时，账户的仓位依赖于券商，所以实盘时不调用此接口。
        """
        daysEngine = dataEngine.daysEngine

        self._curInit()

        # 市场前一交易日
        preDate = daysEngine.tDaysOffsetInDb(date, -1)

        # 载入股票昨日数据，由于可能发生停牌，采用相对日期载入
        if not daysEngine.loadCode(self.code, [preDate, 0], latestAdjFactorInDb=False):
            return False

        # 为了检测当日有没有除权除息，获取昨日收盘
        # !!!对于首日开盘的股票，则返回False
        df = daysEngine.getDataFrame(self.code)
        if df.shape[0] != 1:
            return False
            
        self.preClose = df.ix[0, 'close']

        # 增加持有期
        self.holdingPeriod += 1

        return True

    def _processAdj(self, tick):
        # 回测时@self.preClose不是None，不考虑首日开盘的股票。
        # 实盘时，持仓的同步则由Broker驱动。
        if self.preClose is None:
            return

        if self.sync:
            return

        assert tick.preClose is not None

        if tick.preClose != self.preClose:
            # !!!一定要跟DyStockCtaTemplate的同步策略持仓的复权因子计算方法一致
            priceAdjFactor = self.preClose/tick.preClose

            self.cost /= priceAdjFactor
            self.high /= priceAdjFactor
            self.closeHigh /= priceAdjFactor

            self.availVolume *= priceAdjFactor
            self.totalVolume *= priceAdjFactor

            self.xrd = True

            self.priceAdjFactor = priceAdjFactor
            self.volumeAdjFactor = priceAdjFactor

            # set back so that don't need to adjust factor in loop
            self.preClose = tick.preClose

        else:
            self.priceAdjFactor = 1
            self.volumeAdjFactor = 1

        self.sync = True

    def onTick(self, tick):
        self._processAdj(tick)
            
        self._updatePrice(tick.price, tick.high, tick.low)

    def onBar(self, bar):
        self.onTick(bar)

    def onClose(self):
        """ T+1，收盘后更新持仓 """
        self.availVolume = self.totalVolume

        self.closeHigh = self.price if self.closeHigh is None else max(self.price, self.closeHigh)

    @classmethod
    def restorePos(cls, pos, strategyCls=None):
        """
            根据磁盘的持仓，创建出一个持仓实例
            这个接口只在当日开盘时调用。
        """
        datetime_ = pos['datetime']
        try:
            datetime_ = datetime.strptime(datetime_, '%Y-%m-%d %H:%M:%S')
        except:
            pass

        newPos = cls(datetime_, # string if from broker, else datetime from backtesting or Simu Trader
                     strategyCls,
                     pos['code'],
                     pos['name'],
                     pos['cost'], # take cost as price
                     pos['totalVolume']
                     )

        newPos.holdingPeriod = pos['holdingPeriod'] + 1
        newPos.xrd = pos.get('xrd', False)

        newPos.availVolume = pos['totalVolume'] # set available volume same as total volume
        newPos.high = pos.get('high',  pos['cost'])
        newPos.closeHigh = pos.get('closeHigh')
        newPos.reserved = pos.get('reserved')
        newPos.price = pos.get('price',  pos['cost'])

        return newPos

    def getSavedData(self):
        """
            获取策略持仓收盘要保存的数据
            !!!价格和成交量相关的数据，一定要在@DyStockCtaTemplate.syncPos做前复权处理
            实盘时，策略持仓的很多价格相关的变量是不更新的，比如@self.price。因为从实盘来讲，没有意义。
            @return: dict
        """
        datetime_ = self.datetime
        try:
            datetime_ = self.datetime.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass

        return {'datetime': datetime_,
                'code': self.code,
                'name': self.name,
                'cost': self.cost,
                'high': self.high, # 持有期内最高价格，主要停损时需要
                'closeHigh': self.closeHigh, # 持有期内收盘最高价格，主要停损时需要
                'totalVolume': self.totalVolume,
                'holdingPeriod': self.holdingPeriod,
                'xrd': self.xrd,
                'price': self.price,
                'reserved': self.reserved
                }

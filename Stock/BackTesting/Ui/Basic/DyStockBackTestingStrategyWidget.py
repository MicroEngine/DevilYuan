from DyCommon.Ui.DyTreeWidget import *

from EventEngine.DyEvent import *
from ....Trade.Ui.Basic.DyStockTradeStrategyWidget import * 
from ....Select.Ui.Basic.DyStockSelectStrategyWidget import *


class DyStockBackTestingStrategyWidget(DyStockSelectStrategyWidget):
    """ 只能选中一个策略回测 """

    def __init__(self, paramWidget=None):
        self.__class__.strategyFields = DyStockTradeStrategyWidget.strategyFields
        super().__init__(paramWidget)

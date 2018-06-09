from PyQt5.QtWidgets import QWidget
from PyQt5.Qt import QGridLayout

from .....Select.Ui.Basic.Param.DyStockSelectStrategyParamWidget import *
from .DyStockBackTestingStrategyPeriodsResultWidget import *


class DyStockBackTestingStrategyParamGroupResultWidget(QWidget):
    """ 策略一个参数组合的回测结果窗口
        组成部分：
            参数组合窗口
            多个周期结果窗口
    """

    def __init__(self, strategyCls, paramGroupNo, param, eventEngine, dataEngine, dataViewer):
        super().__init__()

        self._strategyCls = strategyCls
        self._paramGroupNo = paramGroupNo
        self._param = param
        self._eventEngine = eventEngine
        self._dataEngine = dataEngine
        self._dataViewer = dataViewer
        
        self._initUi()

    def _initUi(self):
        self._paramWidget = DyStockSelectStrategyParamWidget()
        self._paramWidget.set(self._param)

        self._periodsResultWidget = DyStockBackTestingStrategyPeriodsResultWidget(self._strategyCls, self._paramGroupNo, self._param, self._eventEngine, self._dataEngine, self._dataViewer)

        grid = QGridLayout()
        grid.setSpacing(0)

        grid.addWidget(self._paramWidget, 0, 0)
        grid.addWidget(self._periodsResultWidget, 1, 0)
        
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 20)

        self.setLayout(grid)

    def newPeriod(self, event):
        self._periodsResultWidget.newPeriod(event)

    def update(self, ackData):
        """ 更新策略参数组合一个回测周期的回测结果 """
        self._periodsResultWidget.update(ackData)

    def removeAll(self):
        self._periodsResultWidget.removeAll()

    def getCurPnlRatio(self):
        return self._periodsResultWidget.getCurPnlRatio()

    def overview(self):
        groupParams = self._paramWidget.get()
        groupNames, groupData = list(groupParams.keys()), list(groupParams.values())

        statsOverviewNames, statsOverviewData = self._periodsResultWidget.overview()

        # add seperator ''
        return groupNames + [''] + statsOverviewNames, groupData + [''] + statsOverviewData
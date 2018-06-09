from ....Strategy.DyStockSelectStrategyTemplate import *
from .....Common.DyStockCommon import *
from .....Common.Ui.Basic.DyStockTableWidget import *
from ....DyStockSelectCommon import *
from ..Dlg.DyStockSelectRefactoryParamsDlg import *


class DyStockSelectStrategySelectResultWidget(DyStockTableWidget):

    def __init__(self, eventEgnine, strategyCls, baseDate, paramWidget=None):
        """
            @strategyCls：选股策略类
            @paramWidget：选股策略的参数窗口
        """
        self._strategyCls = strategyCls

        super().__init__(eventEngine, name=strategyCls.chName, baseDate=baseDate)

        self._eventEngine = eventEngine
        self._baseDate = baseDate
        self._paramWidget = paramWidget

    def _initHeaderMenu(self):
        super()._initHeaderMenu()

        # 策略相关菜单
        menu = QMenu('策略相关')
        self._headerMenu.addMenu(menu)

        action = QAction('重构...', self)
        action.triggered.connect(self._refactoryAct)
        menu.addAction(action)
        action.setEnabled(self._hasRefactory())

    def _initItemMenu(self):
        super()._initItemMenu()

        # 策略相关菜单
        menu = QMenu('策略相关')
        self._itemMenu.addMenu(menu)

        action = QAction('散列图', self)
        action.triggered.connect(self._scatterChartAct)
        menu.addAction(action)
        action.setEnabled(self._hasScatterChart())

    def appendStocks(self, rows, header, autoForegroundColName=None, new=True):
        if autoForegroundColName is None:
            autoForegroundColName = DyStockSelectStrategyTemplate.getAutoColName()

        super().appendStocks(rows, header, autoForegroundColName, new=new)

    def _scatterChartAct(self):
        target, code, date, n = self._getRightClickTargetCodeDateN()
        if target is None: return

        self._dataViewer.plotScatterChart(target, code, date, n)

    def _getRightClickTargetCodeDateN(self):
        item = self.itemAt(self._rightClickPoint)
        if item is None: return None, None, None, None

        if self._paramWidget is None: return None, None, None, None

        code = self[item.row(), '代码']

        param = self._widgetParam.get(self._strategyCls.chName)

        target = param['跟哪个标的比较']
        n = -param['向前N日周期']

        return target, code, self._baseDate, n

    def _refactoryAct(self):
        header, params = self._getRefactoryParams()

        data = {}
        if DyStockSelectRefactoryParamsDlg(data, header, params).exec_():
            self._refactory(data['params'], data['newWindow'])

    def _refactory(self, params, newWindow):
        # 策略的重构方法
        newRows = self._strategyClsRefactory(params)

        if newWindow:
            window = self.__class__(self._eventEngine, self._strategyCls, self._baseDate, self._paramWidget)

            window.appendStocks(newRows, self.getColNames(), self.getAutoForegroundColName())

            window.setWindowTitle(self.name)
            window.showMaximized()

            self._windows.append(window)
        else:
            self.appendStocks(newRows, self.getColNames())

    def _strategyClsRefactory(self, params):
        """
            根据用户自定义参数重构策略选股结果Table的数据显示。
            refactory方法由策略类提供，类方法。
            @params：用户自定义参数
            @return: new rows
        """
        df = self.toDataFrame()

        rows = self._strategyCls.refactory(df, params)

        return rows

    def _hasRefactory(self):
        return self._strategyCls.hasattr('refactory')

    def _getRefactoryParams(self):
        return eval('{0}.getRefactoryParams()'.format(self._strategyClsName))

    def _hasScatterChart(self):
        if '跟哪个标的比较' in self._strategyCls.param:
            return True

        return False






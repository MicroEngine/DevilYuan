from ....Strategy.DyStockSelectStrategyTemplate import *
from .....Common.Ui.Basic.DyStockTableWidget import *
from ..Dlg.DyStockSelectRefactoryParamsDlg import *


class DyStockSelectStrategySelectResultWidget(DyStockTableWidget):

    def __init__(self, eventEngine, strategyCls, baseDate, paramWidget=None):
        """
            @strategyCls：选股策略类
            @paramWidget：选股策略的参数窗口
        """
        self._strategyCls = strategyCls
        
        super().__init__(eventEngine, name=strategyCls.chName, baseDate=baseDate)

        self._paramWidget = paramWidget

    def _initHeaderMenu(self):
        super()._initHeaderMenu()

        self._headerMenu.addSeparator()

        # 策略相关菜单
        menu = self._headerMenu.addMenu('策略相关')

        action = QAction('重构...', self)
        action.triggered.connect(self._refactoryAct)
        menu.addAction(action)
        action.setEnabled(self._hasRefactory())

        action = QAction('贝叶斯统计', self)
        action.triggered.connect(self._bayesianStatsAct)
        menu.addAction(action)
        action.setEnabled(hasattr(self._strategyCls, 'bayesianStats'))

    def _initItemMenu(self):
        super()._initItemMenu()

        self._itemMenu.addSeparator()

        # 策略相关Item菜单
        self._initStrategyItemMenu()

    def _initStrategyItemMenu(self):
        """
            策略相关Item菜单
        """
        menu = self._itemMenu.addMenu('策略相关')

        try:
            self._strategyItemMenuActions = []
            for name, act in self._strategyCls.itemMenu.items():
                action = QAction(name, self)
                action.triggered.connect(self._strategyItemMenuAct)
                menu.addAction(action)
                action.setCheckable(True)

                self._strategyItemMenuActions.append(action)

        except Exception as ex:
            pass

    def _strategyItemMenuAct(self):
        for action in self._strategyItemMenuActions:
            if action.isChecked():
                action.setChecked(False)

                code, name = self.getRightClickCodeName()

                self._strategyCls.itemMenu[action.text()](self._dataViewer, self._paramWidget.get(self._strategyCls.chName), code)

    def appendStocks(self, rows, header, autoForegroundColName=None, new=True):
        if autoForegroundColName is None:
            autoForegroundColName = DyStockSelectStrategyTemplate.getAutoColName()

        super().appendStocks(rows, header, autoForegroundColName, new=new)

    def _bayesianStatsAct(self):
        df = self.toDataFrame()

        self._strategyCls.bayesianStats(df)

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
        return hasattr(self._strategyCls, 'refactory')

    def _getRefactoryParams(self):
        return self._strategyCls.getRefactoryParams()

    def getCustomSaveData(self):
        """
            子类改写
        """
        customData = {'class': 'DyStockSelectStrategySelectResultWidget',
                      'strategyCls': self._strategyCls.name
                      }

        return customData

    def _newWindow(self, rows=None):
        """
            子类改写
        """
        window = self.__class__(self._eventEngine, self._strategyCls, self._baseDate, self._paramWidget)

        if rows is None:
            rows = self.getAll()

        window.appendStocks(rows, self.getColNames(), self.getAutoForegroundColName())

        window.setWindowTitle('{0}[{1}]'.format(self._strategyCls.chName, self._baseDate))
        window.showMaximized()

        self._windows.append(window)

    

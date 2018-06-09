from ....Strategy.DyStockSelectStrategyTemplate import *
from .....Common.Ui.Basic.DyStockTableWidget import *


class DyStockSelectStrategyRegressionPeriodResultWidget(DyStockTableWidget):

    def __init__(self, eventEngine, name, strategyCls, paramWidget=None):
        self._strategyCls = strategyCls

        super().__init__(eventEngine, name=name, index=True)

        self._paramWidget = paramWidget

    def _initHeaderMenu(self):
        super()._initHeaderMenu()

        self._headerMenu.addSeparator()

        # 策略相关菜单
        menu = self._headerMenu.addMenu('策略相关')

        action = QAction('贝叶斯统计', self)
        action.triggered.connect(self._bayesianStatsAct)
        menu.addAction(action)
        action.setEnabled(hasattr(self._strategyCls, 'bayesianStats'))

    def append(self, date, rows):
        for i, row in enumerate(rows):
            if i == 0:
                row.insert(0, date)
                row.insert(0, '*')
            else:
                row.insert(0, date)
                row.insert(0, '')

        self.fastAppendRows(rows, DyStockSelectStrategyTemplate.getAutoColName())

    def getAutoColName(self):
        return DyStockSelectStrategyTemplate.getAutoColName()

    def setColNames(self, names):
        super().setColNames(['*', '基准日期'] + names)

    def rawAppend(self, rows, autoColName):
        self.fastAppendRows(rows, autoColName, True)

    def rawSetColNames(self, names):
        super().setColNames(names)

    def getDateCodeList(self):
        dateCodeList = self.getColumnsData(['基准日期', '代码'])

        return dateCodeList

    def getTargetCodeDateN(self):
        item = self.itemAt(self._rightClickPoint)
        if item is None: return None, None, None, None

        code = self[item.row(), '代码']
        baseDate = self[item.row(), '基准日期']

        param = self._widgetParam.get(self._strategyName)

        target = param['跟哪个标的比较']
        n = -param['向前N日周期']

        return target, code, baseDate, n

    def getRightClickCodeDate(self):
        item = self.itemAt(self._rightClickPoint)
        if item is None: return None, None

        code = self[item.row(), '代码']
        baseDate = self[item.row(), '基准日期']

        return code, baseDate

    def getRightClickCodeName(self):
        item = self.itemAt(self._rightClickPoint)
        if item is None: return None, None

        code = self[item.row(), '代码']
        name = self[item.row(), '名称']

        return code, name

    def getCodeDate(self, item):
        code = self[item.row(), '代码']
        baseDate = self[item.row(), '基准日期']

        return code, baseDate

    def getUniqueName(self):
        """
            子类改写
        """
        return '{0}_{1}'.format(self._strategyCls.chName, self._name)

    def getCustomSaveData(self):
        """
            子类改写
        """
        customData = {'class': 'DyStockSelectStrategyRegressionResultWidget',
                      'strategyCls': self._strategyCls.name
                      }

        return customData

    def _newWindow(self, rows=None):
        """
            子类改写
        """
        window = self.__class__(self._eventEngine, self._name, self._strategyCls, self._paramWidget)

        if rows is None:
            rows = self.getAll()

        window.rawSetColNames(self.getColNames())
        window.rawAppend(rows, self.getAutoForegroundColName())

        window.setWindowTitle('{0}{1}'.format(self._strategyCls.chName, self._name))
        window.showMaximized()

        self._windows.append(window)

    def _bayesianStatsAct(self):
        df = self.toDataFrame()

        df = self._strategyCls.bayesianStats(df, 1)

        # new window
        window = self.__class__(self._eventEngine, self._name, self._strategyCls, self._paramWidget)

        window.rawSetColNames(list(df.columns))
        window.rawAppend(df.values, self.getAutoForegroundColName())

        window.setWindowTitle('{0}{1}'.format(self._strategyCls.chName, self._name))
        window.showMaximized()

        self._windows.append(window)
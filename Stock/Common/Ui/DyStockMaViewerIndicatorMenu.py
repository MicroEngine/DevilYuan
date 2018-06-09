from PyQt5.Qt import QAction


class DyStockMaViewerIndicatorMenu(object):
    """ 设置股票视图显示均线采用的指标 """

    def __init__(self, interface):
        self._interface = interface

        self._init()

    def _init(self):
        menu = self._interface.getMaViewerIndicatorParentMenu()

        maIndicatorMenu = menu.addMenu('均线视图指标')

        # OHLC
        openAction = QAction('开盘价', maIndicatorMenu)
        openAction.triggered.connect(self._act)
        openAction.setCheckable(True)
        maIndicatorMenu.addAction(openAction)

        highAction = QAction('最高价', maIndicatorMenu)
        highAction.triggered.connect(self._act)
        highAction.setCheckable(True)
        maIndicatorMenu.addAction(highAction)

        lowAction = QAction('最低价', maIndicatorMenu)
        lowAction.triggered.connect(self._act)
        lowAction.setCheckable(True)
        maIndicatorMenu.addAction(lowAction)

        closeAction = QAction('收盘价', maIndicatorMenu)
        closeAction.triggered.connect(self._act)
        closeAction.setCheckable(True)
        maIndicatorMenu.addAction(closeAction)

        self._actions = [(openAction, 'open'), (highAction, 'high'), (lowAction, 'low'), (closeAction, 'close')]

        closeAction.setChecked(True)
        self._checkedAction = closeAction
        self._checkedIndicator = 'close'

    def _act(self):
        for action, indicator in self._actions:
            # new indicator
            if action.isChecked() and self._checkedAction != action:
                self._checkedAction = action
                self._checkedIndicator = indicator
                break

        self._checkedAction.setChecked(True)

        for action, indicator in self._actions:
            if self._checkedAction != action:
                action.setChecked(False)

        self._interface.setMaViewerIndicator(self._checkedIndicator)


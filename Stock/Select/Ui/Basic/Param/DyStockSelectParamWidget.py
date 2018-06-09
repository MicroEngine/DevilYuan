from PyQt5 import QtCore
from PyQt5.QtWidgets import QTabWidget

from .DyStockSelectStrategyParamWidget import *


class DyStockSelectParamWidget(QTabWidget):

    def __init__(self):
        super().__init__()

        self._strategyParamWidgets = {}

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._closeTab)

    def set(self, strategyName, paramters, tooltips=None):
        if strategyName not in self._strategyParamWidgets:
            widget = DyStockSelectStrategyParamWidget()
            self.addTab(widget, strategyName)

            # save
            self._strategyParamWidgets[strategyName] = widget

            self._strategyParamWidgets[strategyName].set(paramters)
            self._strategyParamWidgets[strategyName].setToolTip(tooltips)

        self.setCurrentWidget(self._strategyParamWidgets[strategyName])

    def get(self, strategyName):
        return self._strategyParamWidgets[strategyName].get()

    def _closeTab(self, index):
        tabName = self.tabText(index)

        param = self._strategyParamWidgets[tabName].get()
        self._strategyWidget.uncheckStrategy(tabName, param)

        del self._strategyParamWidgets[tabName]

        self.removeTab(index)

    def setStrategyWidget(self, strategyWidget):
        self._strategyWidget = strategyWidget


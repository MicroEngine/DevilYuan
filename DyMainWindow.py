# -*- coding: utf-8 -*-

"""
Module implementing DyMainWindow.
"""
import os
import json

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtWidgets import QMainWindow, QDialog, QAction, QLabel, QCheckBox, QTextEdit, QPushButton, QGridLayout

import matplotlib
matplotlib.use('Qt5Agg')

# From DevilYuan
from DyCommon.DyCommon import DyCommon
from Stock.Common.DyStockCommon import DyStockCommon
from Stock.Trade.Ui.DyStockTradeMainWindow import DyStockTradeMainWindow
from Stock.Data.Ui.DyStockDataMainWindow import DyStockDataMainWindow
from Stock.BackTesting.Ui.DyStockBackTestingMainWindow import DyStockBackTestingMainWindow
from Stock.Select.Ui.DyStockSelectMainWindow import DyStockSelectMainWindow
from Stock.Config.DyStockConfig import DyStockConfig
from Stock.Config.DyStockHistDaysDataSourceConfigDlg import DyStockHistDaysDataSourceConfigDlg
from Stock.Config.DyStockMongoDbConfigDlg import DyStockMongoDbConfigDlg
from Stock.Config.Trade.DyStockWxScKeyConfigDlg import DyStockWxScKeyConfigDlg
from Stock.Config.Trade.DyStockAccountConfigDlg import DyStockAccountConfigDlg


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(473, 235)
        self.centralWidget = QtWidgets.QWidget(MainWindow)
        self.centralWidget.setObjectName("centralWidget")
        self.pushButtonSelectStock = QtWidgets.QPushButton(self.centralWidget)
        self.pushButtonSelectStock.setGeometry(QtCore.QRect(10, 10, 221, 91))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(20)
        self.pushButtonSelectStock.setFont(font)
        self.pushButtonSelectStock.setObjectName("pushButtonSelectStock")
        self.pushButtonStockTrade = QtWidgets.QPushButton(self.centralWidget)
        self.pushButtonStockTrade.setGeometry(QtCore.QRect(240, 10, 221, 91))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(20)
        self.pushButtonStockTrade.setFont(font)
        self.pushButtonStockTrade.setObjectName("pushButtonStockTrade")
        self.pushButtonStockData = QtWidgets.QPushButton(self.centralWidget)
        self.pushButtonStockData.setGeometry(QtCore.QRect(240, 110, 221, 91))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(20)
        self.pushButtonStockData.setFont(font)
        self.pushButtonStockData.setObjectName("pushButtonStockData")
        self.pushButtonStockStrategyBackTestinig = QtWidgets.QPushButton(self.centralWidget)
        self.pushButtonStockStrategyBackTestinig.setGeometry(QtCore.QRect(10, 110, 221, 91))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(20)
        self.pushButtonStockStrategyBackTestinig.setFont(font)
        self.pushButtonStockStrategyBackTestinig.setObjectName("pushButtonStockStrategyBackTestinig")
        MainWindow.setCentralWidget(self.centralWidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "魔元量化"))
        self.pushButtonSelectStock.setText(_translate("MainWindow", "选股"))
        self.pushButtonStockTrade.setText(_translate("MainWindow", "股票交易"))
        self.pushButtonStockData.setText(_translate("MainWindow", "股票数据"))
        self.pushButtonStockStrategyBackTestinig.setText(_translate("MainWindow", "股票策略回测"))


class DyMainWindow(QMainWindow, Ui_MainWindow):
    """
    Class documentation goes here.
    """
    from pylab import mpl
    mpl.rcParams['font.sans-serif'] = ['SimHei']
    mpl.rcParams['axes.unicode_minus'] = False

    def __init__(self, parent=None):
        """
        Constructor
        
        @param parent reference to the parent widget
        @type QWidget
        """
        super(DyMainWindow, self).__init__(parent)
        self.setupUi(self)

        self.setWindowFlags(Qt.WindowMinimizeButtonHint|Qt.WindowCloseButtonHint)
        self.setFixedSize(self.width(), self.height())

        # menu
        self._initMenu()

        # config
        self._config()
    
    @pyqtSlot()
    def on_pushButtonSelectStock_clicked(self):
        """
        Slot documentation goes here.
        """
        # TODO: not implemented yet
        DyStockSelectMainWindow(self).show()
    
    @pyqtSlot()
    def on_pushButtonStockTrade_clicked(self):
        """
        Slot documentation goes here.
        """
        # TODO: not implemented yet
        DyStockTradeMainWindow(self).show()

    @pyqtSlot()
    def on_pushButtonStockData_clicked(self):
        """
        Slot documentation goes here.
        """
        # TODO: not implemented yet
        DyStockDataMainWindow(self).show()

    @pyqtSlot()
    def on_pushButtonStockStrategyBackTestinig_clicked(self):
        """
        Slot documentation goes here.
        """
        # TODO: not implemented yet
        DyStockBackTestingMainWindow(self).show()

    def _initMenu(self):
        # 创建菜单
        menuBar = self.menuBar()
        
        # 添加菜单
        menu = menuBar.addMenu('配置')

        action = QAction('股票历史日线数据源...', self)
        action.triggered.connect(self._configStockHistDaysDataSource)
        menu.addAction(action)

        action = QAction('MongoDB...', self)
        action.triggered.connect(self._configMongoDb)
        menu.addAction(action)

        subMenu = menu.addMenu('实盘交易')
        action = QAction('微信...', self)
        action.triggered.connect(self._configWx)
        subMenu.addAction(action)

        action = QAction('账号...', self)
        action.triggered.connect(self._configAccount)
        subMenu.addAction(action)

    def _configStockHistDaysDataSource(self):
        DyStockHistDaysDataSourceConfigDlg().exec_()

    def _configMongoDb(self):
        DyStockMongoDbConfigDlg().exec_()

    def _configWx(self):
        DyStockWxScKeyConfigDlg().exec_()

    def _configAccount(self):
        DyStockAccountConfigDlg().exec_()

    def _config(self):
        DyStockConfig.config()


if __name__ == "__main__":

    """
    import ctypes
    whnd = ctypes.windll.kernel32.GetConsoleWindow()
    if whnd != 0:
        ctypes.windll.user32.ShowWindow(whnd, 0)
        ctypes.windll.kernel32.CloseHandle(whnd)
    """

    import ctypes
    import platform

    # 设置Windows底部任务栏图标
    if 'Windows' in platform.uname() :
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('DevilYuan')


    import sys
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon('DevilYuan.jpg'))
    MainWindow = DyMainWindow()
    MainWindow.show()

    import qdarkstyle
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    sys.exit(app.exec_())

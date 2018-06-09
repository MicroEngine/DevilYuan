import json

from PyQt5.QtWidgets import QDialog, QLabel, QTabWidget, QLineEdit, QPushButton, QGridLayout, QGridLayout, QWidget

from DyCommon.DyCommon import DyCommon
from Stock.Common.DyStockCommon import DyStockCommon
from ..DyStockConfig import DyStockConfig


class DyStockAccountConfigDlg(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._read()
        self._initUi()

    def _createThsTab(self):
        widget = QWidget()

        # 控件
        labelAccount = QLabel('账号')
        labelPassword = QLabel('密码')
        self._lineEditAccountThs = QLineEdit(self._data["Ths"]["Account"])
        self._lineEditPasswordThs = QLineEdit(self._data["Ths"]["Password"])

        labelExe = QLabel('同花顺下单可执行文件路径                                                                             ')
        self._lineEditExeThs = QLineEdit(self._data["Ths"]["Exe"])

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(labelAccount, 0, 0, 1, 1)
        grid.addWidget(self._lineEditAccountThs, 0, 1, 1, 9)
        grid.addWidget(labelPassword, 0, 10, 1, 1)
        grid.addWidget(self._lineEditPasswordThs, 0, 11, 1, 9)

        grid.addWidget(QLabel(" "), 2, 0)

        grid.addWidget(labelExe, 3, 0, 1, 20)
        grid.addWidget(self._lineEditExeThs, 4, 0, 1, 20)

        widget.setLayout(grid)

        self._tabWidget.addTab(widget, "同花顺")

    def _createYhTab(self):
        widget = QWidget()

        # 控件
        labelAccount = QLabel('账号')
        labelPassword = QLabel('密码')
        self._lineEditAccountYh = QLineEdit(self._data["Yh"]["Account"])
        self._lineEditPasswordYh = QLineEdit(self._data["Yh"]["Password"])

        labelExe = QLabel('银河证券客户端可执行文件路径                                                                             ')
        self._lineEditExeYh = QLineEdit(self._data["Yh"]["Exe"])

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(labelAccount, 0, 0, 1, 1)
        grid.addWidget(self._lineEditAccountYh, 0, 1, 1, 9)
        grid.addWidget(labelPassword, 0, 10, 1, 1)
        grid.addWidget(self._lineEditPasswordYh, 0, 11, 1, 9)

        grid.addWidget(QLabel(" "), 2, 0)

        grid.addWidget(labelExe, 3, 0, 1, 20)
        grid.addWidget(self._lineEditExeYh, 4, 0, 1, 20)

        widget.setLayout(grid)

        self._tabWidget.addTab(widget, "银河证券")

    def _initUi(self):
        self.setWindowTitle('配置-账号（实盘交易）')

        self._tabWidget = QTabWidget()
        self._createYhTab()
        self._createThsTab()
        
        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(self._tabWidget, 0, 0, 2, 1)

        grid.addWidget(okPushButton, 0, 1)
        grid.addWidget(cancelPushButton, 1, 1)
 
        self.setLayout(grid)

    def _read(self):
        file = DyStockConfig.getStockAccountFileName()

        # open
        try:
            with open(file) as f:
                self._data = json.load(f)
        except:
            self._data = DyStockConfig.defaultAccount

    def _ok(self):
        # get data from UI
        data = {"Ths": {}, "Yh": {}}

        # 银河证券
        data["Yh"]["Account"] = self._lineEditAccountYh.text()
        data["Yh"]["Password"] = self._lineEditPasswordYh.text()
        data["Yh"]["Exe"] = self._lineEditExeYh.text()

        # 同花顺
        data["Ths"]["Account"] = self._lineEditAccountThs.text()
        data["Ths"]["Password"] = self._lineEditPasswordThs.text()
        data["Ths"]["Exe"] = self._lineEditExeThs.text()

        # config to variables
        DyStockConfig.configStockAccount(data)

        # save config
        file = DyStockConfig.getStockAccountFileName()
        with open(file, 'w') as f:
            f.write(json.dumps(data, indent=4))

        self.accept()

    def _cancel(self):
        self.reject()
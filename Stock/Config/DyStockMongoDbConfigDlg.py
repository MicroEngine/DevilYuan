import json

from PyQt5.QtWidgets import QDialog, QLabel, QTabWidget, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget

from DyCommon.DyCommon import DyCommon
from Stock.Common.DyStockCommon import DyStockCommon
from .DyStockConfig import DyStockConfig


class DyStockMongoDbConfigDlg(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._read()
        self._initUi()

    def _createCommonDaysTab(self, tabWidget):
        widget = QTabWidget()

        self._createWindTab(widget)
        self._createTuShareTab(widget)

        tabWidget.addTab(widget, "通用和日线数据")

    def _createWindTab(self, tabWidget):
        widget = QWidget()

        # common data
        labelStockCommonDb = QLabel('股票通用数据库')
        labelTradeDayTableName = QLabel('股票交易日数据库表')
        labelCodeTableName = QLabel('股票代码数据库表')

        self._lineEditStockCommonDbWind = QLineEdit(self._data["CommonDays"]["Wind"]['stockCommonDb'])
        self._lineEditTradeDayTableNameWind = QLineEdit(self._data["CommonDays"]["Wind"]['tradeDayTableName'])
        self._lineEditCodeTableNameWind = QLineEdit(self._data["CommonDays"]["Wind"]['codeTableName'])

        # days data
        labelStockDaysDb = QLabel('股票历史日线数据库')
        self._lineEditStockDaysDbWind = QLineEdit(self._data["CommonDays"]["Wind"]['stockDaysDb'])

        # 布局
        vbox = QVBoxLayout()
 
        vbox.addWidget(labelStockCommonDb)
        vbox.addWidget(self._lineEditStockCommonDbWind)
        vbox.addWidget(labelTradeDayTableName)
        vbox.addWidget(self._lineEditTradeDayTableNameWind)
        vbox.addWidget(labelCodeTableName)
        vbox.addWidget(self._lineEditCodeTableNameWind)

        vbox.addWidget(QLabel('                                                                                             '))

        vbox.addWidget(labelStockDaysDb)
        vbox.addWidget(self._lineEditStockDaysDbWind)
 
        widget.setLayout(vbox)

        tabWidget.addTab(widget, "Wind")

    def _createTuShareTab(self, tabWidget):
        widget = QWidget()

        # common data
        labelStockCommonDb = QLabel('股票通用数据库')
        labelTradeDayTableName = QLabel('股票交易日数据库表')
        labelCodeTableName = QLabel('股票代码数据库表')

        self._lineEditStockCommonDbTuShare = QLineEdit(self._data["CommonDays"]["TuShare"]['stockCommonDb'])
        self._lineEditTradeDayTableNameTuShare = QLineEdit(self._data["CommonDays"]["TuShare"]['tradeDayTableName'])
        self._lineEditCodeTableNameTuShare = QLineEdit(self._data["CommonDays"]["TuShare"]['codeTableName'])

        # days data
        labelStockDaysDb = QLabel('股票历史日线数据库')
        self._lineEditStockDaysDbTuShare = QLineEdit(self._data["CommonDays"]["TuShare"]['stockDaysDb'])

        # 布局
        vbox = QVBoxLayout()
 
        vbox.addWidget(labelStockCommonDb)
        vbox.addWidget(self._lineEditStockCommonDbTuShare)
        vbox.addWidget(labelTradeDayTableName)
        vbox.addWidget(self._lineEditTradeDayTableNameTuShare)
        vbox.addWidget(labelCodeTableName)
        vbox.addWidget(self._lineEditCodeTableNameTuShare)

        vbox.addWidget(QLabel('                                                                                             '))

        vbox.addWidget(labelStockDaysDb)
        vbox.addWidget(self._lineEditStockDaysDbTuShare)
 
        widget.setLayout(vbox)

        tabWidget.addTab(widget, "TuShare")

    def _createConnectionTab(self, tabWidget):
        widget = QWidget()

        labelHost = QLabel('主机')
        labelPort = QLabel('端口')

        self._lineEditHost = QLineEdit(self._data['Connection']["Host"])
        self._lineEditPort = QLineEdit(str(self._data['Connection']["Port"]))

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(labelHost, 0, 0)
        grid.addWidget(self._lineEditHost, 0, 1)

        grid.addWidget(labelPort, 0, 2)
        grid.addWidget(self._lineEditPort, 0, 3)
 
        widget.setLayout(grid)

        tabWidget.addTab(widget, "连接")

    def _createTicksTab(self, tabWidget):
        widget = QWidget()

        labelStockTicksDb = QLabel('股票分笔数据库')
        self._lineEditStockTicksDb = QLineEdit(self._data["Ticks"]['db'])

        # 布局
        hbox = QHBoxLayout()
 
        hbox.addWidget(labelStockTicksDb)
        hbox.addWidget(self._lineEditStockTicksDb)
 
        widget.setLayout(hbox)

        tabWidget.addTab(widget, "分笔数据")

    def _initUi(self):
        self.setWindowTitle('配置-MongoDB')

        tabWidget = QTabWidget()
        self._createConnectionTab(tabWidget)
        self._createCommonDaysTab(tabWidget)
        self._createTicksTab(tabWidget)
        

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(tabWidget, 0, 0, 2, 1)

        grid.addWidget(okPushButton, 0, 1)
        grid.addWidget(cancelPushButton, 1, 1)
 
        self.setLayout(grid)

    def _read(self):
        file = DyStockConfig.getStockMongoDbFileName()

        # open
        try:
            with open(file) as f:
                self._data = json.load(f)
        except:
            self._data = DyStockConfig.defaultMongoDb

    def _ok(self):
        # get data from UI
        data = {"Connection": {}, "CommonDays": {"Wind": {}, "TuShare": {}}, "Ticks": {}}

        # host & port
        data["Connection"]["Host"] = self._lineEditHost.text()
        data["Connection"]["Port"] = int(self._lineEditPort.text())

        # Wind
        data["CommonDays"]["Wind"]['stockCommonDb'] = self._lineEditStockCommonDbWind.text()
        data["CommonDays"]["Wind"]['tradeDayTableName'] = self._lineEditTradeDayTableNameWind.text()
        data["CommonDays"]["Wind"]['codeTableName'] = self._lineEditCodeTableNameWind.text()
        data["CommonDays"]["Wind"]['stockDaysDb'] = self._lineEditStockDaysDbWind.text()

        # TuShare
        data["CommonDays"]["TuShare"]['stockCommonDb'] = self._lineEditStockCommonDbTuShare.text()
        data["CommonDays"]["TuShare"]['tradeDayTableName'] = self._lineEditTradeDayTableNameTuShare.text()
        data["CommonDays"]["TuShare"]['codeTableName'] = self._lineEditCodeTableNameTuShare.text()
        data["CommonDays"]["TuShare"]['stockDaysDb'] = self._lineEditStockDaysDbTuShare.text()

        # ticks
        data["Ticks"]['db'] = self._lineEditStockTicksDb.text()

        # config to variables
        DyStockConfig.configStockMongoDb(data)

        # save config
        file = DyStockConfig.getStockMongoDbFileName()
        with open(file, 'w') as f:
            f.write(json.dumps(data, indent=4))

        self.accept()

    def _cancel(self):
        self.reject()
import json

from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout

from DyCommon.DyCommon import DyCommon
from Stock.Common.DyStockCommon import DyStockCommon
from ..DyStockConfig import DyStockConfig


class DyStockWxScKeyConfigDlg(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._read()
        self._initUi()
        
    def _initUi(self):
        self.setWindowTitle('配置-微信（实盘交易）')
 
        # 控件
        label = QLabel('Sever酱（方糖）的SCKEY                                                                                    ')

        self._lineEditScKey = QLineEdit(self._data["WxScKey"])

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        vbox = QVBoxLayout()
 
        vbox.addWidget(label)
        vbox.addWidget(self._lineEditScKey)

        vbox.addWidget(QLabel(" "))

        vbox.addWidget(okPushButton)
        vbox.addWidget(cancelPushButton)
 
        self.setLayout(vbox)

    def _read(self):
        file = DyStockConfig.getStockWxScKeyFileName()

        # open
        try:
            with open(file) as f:
                self._data = json.load(f)
        except:
            self._data = DyStockConfig.defaultWxScKey

    def _ok(self):
        # get data from UI
        data = {"WxScKey": self._lineEditScKey.text()}

        # config to variables
        DyStockConfig.configStockWxScKey(data)

        # save config
        file = DyStockConfig.getStockWxScKeyFileName()
        with open(file, 'w') as f:
            f.write(json.dumps(data, indent=4))

        self.accept()

    def _cancel(self):
        self.reject()
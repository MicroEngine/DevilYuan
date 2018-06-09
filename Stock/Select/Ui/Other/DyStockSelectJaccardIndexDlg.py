from datetime import *

from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton


class DyStockSelectJaccardIndexDlg(QDialog):

    def __init__(self, data, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi()

    def _initUi(self):
        self.setWindowTitle('杰卡德指数')
 
        # 控件
        label = QLabel('参数(格式: 周期1,涨幅1(%);周期2,涨幅2(%);..., 比如10,10;20,20;...)')
        self._lineEdit = QLineEdit('10,10;20,20;30,30;40,40;50,50;60,60')

        startDateLable = QLabel('开始日期')
        self._startDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        endDateLable = QLabel('结束日期')
        self._endDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(startDateLable, 0, 0)
        grid.addWidget(self._startDateLineEdit, 1, 0)

        grid.addWidget(endDateLable, 0, 1)
        grid.addWidget(self._endDateLineEdit, 1, 1)
 
        grid.addWidget(label, 2, 0, 1, 2)
        grid.addWidget(self._lineEdit, 3, 0, 1, 2)

        grid.addWidget(okPushButton, 4, 1)
        grid.addWidget(cancelPushButton, 4, 0)
 
        self.setLayout(grid)

    def _ok(self):
        self._data['startDate'] = self._startDateLineEdit.text()
        self._data['endDate'] = self._endDateLineEdit.text()

        param = self._lineEdit.text()
        param = param.split(';')
        paramDict = {}
        for param_ in param:
            day, increase = param_.split(',')
            paramDict[int(day)] = int(increase)

        self._data['param'] = paramDict

        self.accept()

    def _cancel(self):
        self.reject()

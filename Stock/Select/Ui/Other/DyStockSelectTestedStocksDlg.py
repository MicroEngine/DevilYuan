from datetime import *
import os
import re

from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QTextEdit, QPushButton, QApplication

from DyCommon.DyCommon import *


class DyStockSelectTestedStocksDlg(QDialog):

    def __init__(self, data, parent=None):
        super().__init__(parent)

        self._data = data

        self._init()
        self._initUi()

    def _init(self):
        path = DyCommon.createPath('Stock/User/Config/Testing')
        self._file = os.path.join(path, 'DyStockSelectTestedStocks.dy')

    def _read(self):
        if os.path.exists(self._file):
            with open(self._file) as f:
                codes = f.read()
        else:
            codes = ""

        return codes

    def _save(self):
        with open(self._file, 'w') as f:
            f.write(self._codesTextEdit.toPlainText())

    def _initUi(self):
        self.setWindowTitle('要调试的股票')
 
        # 控件
        descriptionLabel = QLabel('要调试的股票代码')
        self._codesTextEdit = QTextEdit()
        self._codesTextEdit.setPlainText(self._read())

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(descriptionLabel, 0, 0)

        grid.addWidget(self._codesTextEdit, 1, 0, 20, 10)
 
        grid.addWidget(okPushButton, 1, 11)
        grid.addWidget(cancelPushButton, 2, 11)
 
 
        self.setLayout(grid)
        self.resize(QApplication.desktop().size().width()//3, QApplication.desktop().size().height()//2)

    def _ok(self):
        # save
        self._save()

        # set out data
        codes = re.split(',|\n| ', self._codesTextEdit.toPlainText())
        temp = []
        for x in codes:
            if x and x not in temp: temp.append(x)

        codes = [x + '.SH' if x[0] in ['6', '5'] else x + '.SZ' for x in temp]

        self._data['codes'] = codes

        self.accept()

    def _cancel(self):
        self.reject()

from datetime import datetime

from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton


class DyCodeDateDlg(QDialog):

    def __init__(self, codeLabelText, data, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi(codeLabelText)

    def _initUi(self, codeLabelText):
        self.setWindowTitle('代码日期')
 
        # 控件
        codeLable = QLabel(codeLabelText)
        self._codeLineEdit = QLineEdit()
        codes = self._data.get('codes')
        if codes:
            self._codeLineEdit.setText(','.join(codes))

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
 
        grid.addWidget(codeLable, 2, 0, 1, 2)
        grid.addWidget(self._codeLineEdit, 3, 0, 1, 2)

        grid.addWidget(okPushButton, 4, 1)
        grid.addWidget(cancelPushButton, 4, 0)
 
        self.setLayout(grid)

    def _ok(self):
        self._data['startDate'] = self._startDateLineEdit.text()
        self._data['endDate'] = self._endDateLineEdit.text()

        codes = self._codeLineEdit.text()
        self._data['codes'] = codes.split(',') if codes else None

        self.accept()

    def _cancel(self):
        self.reject()

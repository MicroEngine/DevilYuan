from PyQt5.QtWidgets import QApplication, QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QCheckBox


class DyStockSelectIndustryCompareDlg(QDialog):

    def __init__(self, name, baseDate, data, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi(name, baseDate)

    def _initUi(self, name, baseDate):
        self.setWindowTitle('行业对比[{0}]-基准日期[{1}]'.format(name, baseDate))
 
        # 控件
        forwardNTDaysLabel = QLabel('向前N日涨幅(%)')
        self._forwardNTDaysLineEdit = QLineEdit('30')

        self._industry2CheckBox = QCheckBox('行业二级分级')
        #self._industry2CheckBox.setChecked(True)

        self._industry3CheckBox = QCheckBox('行业三级分级')
        self._industry3CheckBox.setChecked(True)

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(forwardNTDaysLabel, 0, 0)
        grid.addWidget(self._forwardNTDaysLineEdit, 0, 1)

        grid.addWidget(self._industry2CheckBox, 1, 0)
        grid.addWidget(self._industry3CheckBox, 1, 1)

        grid.addWidget(okPushButton, 2, 1)
        grid.addWidget(cancelPushButton, 2, 0)
 
        self.setLayout(grid)

        self.setMinimumWidth(QApplication.desktop().size().width()//5)

    def _ok(self):
        self._data['forwardNTDays'] = int(self._forwardNTDaysLineEdit.text())

        self._data['industry2'] = self._industry2CheckBox.isChecked()
        self._data['industry3'] = self._industry3CheckBox.isChecked()

        self.accept()

    def _cancel(self):
        self.reject()

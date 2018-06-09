from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton


class DyStockSelectDayKChartPeriodDlg(QDialog):

    def __init__(self, data, parent=None):
        super(DyStockSelectDayKChartPeriodDlg, self).__init__(parent)

        self._data = data

        self._initUi()

    def _initUi(self):
        self.setWindowTitle('日K线前后交易日周期')
 
        # 控件
        dayKChartPeriodLable = QLabel('股票(指数)日K线前后交易日周期')
        self._dayKChartPeriodLineEdit = QLineEdit(str(self._data['periodNbr']) if self._data else '60' )

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(dayKChartPeriodLable, 0, 0, 1, 2)
        grid.addWidget(self._dayKChartPeriodLineEdit, 1, 0, 1, 2)

        grid.addWidget(okPushButton, 2, 1)
        grid.addWidget(cancelPushButton, 2, 0)
 
 
        self.setLayout(grid)

    def _ok(self):
        self._data['periodNbr'] = int(self._dayKChartPeriodLineEdit.text())

        self.accept()

    def _cancel(self):
        self.reject()




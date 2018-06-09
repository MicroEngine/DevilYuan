from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton


class DyProcessNbrDlg(QDialog):

    def __init__(self, data, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi()

    def _initUi(self):
        self.setWindowTitle('进程数')
 
        # 控件
        processNbrLable = QLabel('进程数')
        self._processNbrLineEdit = QLineEdit(str(self._data['nbr']) if self._data else '0' )

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(processNbrLable, 0, 0)
        grid.addWidget(self._processNbrLineEdit, 1, 0, 1, 2)

        grid.addWidget(okPushButton, 2, 1)
        grid.addWidget(cancelPushButton, 2, 0)
 
 
        self.setLayout(grid)

    def _ok(self):
        self._data['nbr'] = int(self._processNbrLineEdit.text())

        self.accept()

    def _cancel(self):
        self.reject()

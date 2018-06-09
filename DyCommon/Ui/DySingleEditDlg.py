from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton


class DySingleEditDlg(QDialog):

    def __init__(self, data, title, label, default='', parent=None):
        """
            @default: LineEdit initial value
        """
        super().__init__(parent)

        self._data = data

        self._initUi(title, label, default)

    def _initUi(self, title, label, default):
        self.setWindowTitle(title)
 
        # 控件
        label_ = QLabel(label)
        self._lineEdit = QLineEdit(str(self._data['data']) if self._data else str(default) )

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(label_, 0, 0, 1, 2)
        grid.addWidget(self._lineEdit, 0, 2, 1, 2)

        grid.addWidget(okPushButton, 1, 2, 1, 2)
        grid.addWidget(cancelPushButton, 1, 0, 1, 2)
 
 
        self.setLayout(grid)

    def _ok(self):
        text = self._lineEdit.text()

        try:
            self._data['data'] = int(text)
        except Exception as ex:
            self._data['data'] = text

        self.accept()

    def _cancel(self):
        self.reject()
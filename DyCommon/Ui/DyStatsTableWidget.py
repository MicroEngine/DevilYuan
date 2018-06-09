import re
from PyQt5 import QtCore

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

from DyCommon.DyCommon import *
from DyCommon.Ui.DyTableWidget import *
from DyCommon.Ui.DyDataFrameWindow import *


class DyStatsTableWidget(DyTableWidget):

    def __init__(self, parent=None, readOnly=False, index=True, floatCut=True, autoScroll=True, floatRound=2):
        super().__init__(parent=parent, readOnly=readOnly, index=index, floatCut=floatCut, autoScroll=autoScroll, floatRound=floatRound)

        self._initHeaderMenu()

    def _initHeaderMenu(self):
        """ 初始化表头右键菜单 """
        # 设置表头右键菜单事件
        headers = self.horizontalHeader()
        headers.setContextMenuPolicy(Qt.CustomContextMenu)
        headers.customContextMenuRequested.connect(self._showHeaderContextMenu)

        # 创建菜单
        self._headerMenu = QMenu(self)
        
        # 创建操作
        action = QAction('设为自动前景色关键列', self)
        action.triggered.connect(self._setAutoForegroundColAct)
        self._headerMenu.addAction(action)

        self._headerMenu.addSeparator()

        action = QAction('描述统计', self)
        action.triggered.connect(self._describeAct)
        self._headerMenu.addAction(action)

        action = QAction('散列图矩阵', self)
        action.triggered.connect(self._scatterMatrixAct)
        self._headerMenu.addAction(action)

        # 列跟列之间的散列图，根据列名动态创建
        self.__scatterMenu = self._headerMenu.addMenu('散列图')
        self.__scatterActions = []

        action = QAction('概率分布', self)
        action.triggered.connect(self._probDistAct)
        self._headerMenu.addAction(action)

        action = QAction('词汇统计', self)
        action.triggered.connect(self._wordStatsAct)
        self._headerMenu.addAction(action)

    def _showHeaderContextMenu(self, position):
        self._rightClickHeaderCol = self.horizontalHeader().logicalIndexAt(position)
        self._rightClickHeaderItem = self.horizontalHeaderItem(self._rightClickHeaderCol)

        # 动态创建每个列的散列图操作
        self.__createScatterActions()

        # call virtual method so that child class can customize the context menu of headers
        self.customizeHeaderContextMenu(self._rightClickHeaderItem)

        self._headerMenu.popup(QCursor.pos())

    def customizeHeaderContextMenu(self, headerItem):
        """
            子类改写
            这样子类可以定制Header的右键菜单
        """
        pass

    def __createScatterActions(self):
        for action in self.__scatterActions:
            self.__scatterMenu.removeAction(action)
            del action

        self.__scatterActions = []

        colNames = self.getColNames()

        for name in colNames:
            if name in ['*', '基准日期', '代码', '名称']:
                continue

            action = QAction(name, self)
            action.triggered.connect(self.__scatterAct)
            action.setCheckable(True)
            self.__scatterMenu.addAction(action)

            self.__scatterActions.append(action)

    def __countQuadrant(self, xName, yName, data):
        """
            统计象限点的个数
        """
        # assume all are numbers except time
        xOrg, xNumber = (datetime.strptime('2000-01-01 12:00:00', '%Y-%m-%d %H:%M:%S'), False) if '时间' in xName else (0, True)
        yOrg, yNumber = (datetime.strptime('2000-01-01 12:00:00', '%Y-%m-%d %H:%M:%S'), False) if '时间' in yName else (0, True)

        # 过滤非time和数字，并统计每个象限的个数占比
        newData = []
        quadrantNbr = [0]*4
        lineNbr = 0
        for x, y in data:
            if x is None or y is None:
                continue

            try:
                if xNumber:
                    x = float(x)
                else:
                    x = datetime.strptime('2000-01-01 ' + x, '%Y-%m-%d %H:%M:%S')

                if yNumber:
                    y = float(y)
                else:
                    y = datetime.strptime('2000-01-01 ' + y, '%Y-%m-%d %H:%M:%S')
            except Exception:
                continue

            newData.append([x, y])

            if x > xOrg and y > yOrg:
                quadrantNbr[0] += 1
            elif x < xOrg and y > yOrg:
                quadrantNbr[1] += 1
            elif x < xOrg and y < yOrg:
                quadrantNbr[2] += 1
            elif x > xOrg and y < yOrg:
                quadrantNbr[3] += 1

            else: # 象限坐标上的点数
                lineNbr += 1

        return newData, lineNbr, quadrantNbr

    def __timeScatter(self, xName, yName, data):
        """
            日内time散列图
            @data: [[x, y]]
        """
        def _getTime(data):
            """ get range of time """
            timeMin = min(data)
            timeMax = max(data)

            assert timeMax.hour < 24
            timeMin = datetime(2000, 1, 1, timeMin.hour)
            timeMax = datetime(2000, 1, 1, timeMax.hour + 1)

            return timeMin, timeMax

        # count point numbers for each quadrant
        newData, lineNbr, quadrantNbr = self.__countQuadrant(xName, yName, data)
        if not newData:
            return

        totalNbr = len(newData)

        quadrantRatio = ['%.2f'%(x/totalNbr*100) for x in quadrantNbr]
        lineRatio = '%.2f'%(lineNbr/totalNbr*100)

        # transform
        xData, yData = [], []
        for x, y in newData:
            xData.append(x)
            yData.append(y)

        # plot
        DyMatplotlib.newFig()

        fig = plt.gcf()
        ax = fig.add_subplot(1, 1, 1)
        ax.grid(True)
        
        # set x ticks
        if '时间' in xName:
            timeMin, timeMax = _getTime(xData)

            # position of the labels
            loc = [timeMin + timedelta(hours=i) for i in np.arange(0, timeMax.hour - timeMin.hour + 0.5, 0.5)]
            ax.set_xticks(loc)

            # format of the labels
            fmt = DateFormatter('%H:%M')
            ax.xaxis.set_major_formatter(fmt)

            # set axis limits
            ax.axis(xmin=timeMin, xmax=timeMax)

            ax.axvline(datetime(2000, 1, 1, 12), color='r', alpha=.5)
        else:
            ax.axvline(0, color='r', alpha=.5)

        # set y ticks
        if '时间' in yName:
            timeMin, timeMax = _getTime(yData)

            # position of the labels
            loc = [timeMin + timedelta(hours=i) for i in np.arange(0, timeMax.hour - timeMin.hour + 0.5, 0.5)]
            ax.set_yticks(loc)

            # format of the labels
            fmt = DateFormatter('%H:%M')
            ax.yaxis.set_major_formatter(fmt)

            # set axis limits
            ax.axis(ymin=timeMin, ymax=timeMax)

            ax.axhline(datetime(2000, 1, 1, 12), color='r', alpha=.5)
        else:
            ax.axhline(0, color='r', alpha=.5)

        # scatter
        ax.scatter(xData, yData)

        ax.set_title('象限[1, 2, 3, 4]占比{}%, 象限坐标占比{}%, 总数{}'.format(quadrantRatio, lineRatio, totalNbr))
        ax.set_xlabel(xName)
        ax.set_ylabel(yName)

        fig.show()

    def __numberScatter(self, xName, yName, data):
        """
            数字散列图
        """
        # count point numbers for each quadrant
        newData, lineNbr, quadrantNbr = self.__countQuadrant(xName, yName, data)
        if not newData:
            return

        totalNbr = len(newData)

        quadrantRatio = ['%.2f'%(x/totalNbr*100) for x in quadrantNbr]
        lineRatio = '%.2f'%(lineNbr/totalNbr*100)

        # DF
        df = pd.DataFrame(data=newData, columns=[xName, yName])

        # plot
        DyMatplotlib.newFig()

        df.plot.scatter(x=xName, y=yName)
            
        f = plt.gcf()
        f.axes[0].grid(True)
        f.axes[0].axhline(0, color='r', alpha=.5)
        f.axes[0].axvline(0, color='r', alpha=.5)
        f.axes[0].set_title('象限[1, 2, 3, 4]占比{}%, 象限坐标占比{}%, 总数{}'.format(quadrantRatio, lineRatio, totalNbr))

        f.show()

    def __scatterAct(self):
        for action in self.__scatterActions:
            if not action.isChecked():
                continue

            action.setChecked(False)

            # get x&y data
            xName = self._rightClickHeaderItem.text()
            yName = action.text()

            data = self.getColumnsData([xName, yName])

            # scatter
            if '时间' in xName or '时间' in yName:
                self.__timeScatter(xName, yName, data)
            else:
                self.__numberScatter(xName, yName, data)

            break

    def _isNonNbrColName(self, colName):
        if colName == 'Org.' or colName == '*' or colName == '代码' or colName == '名称' or '日期' in colName:
            return True

        return False

    def _setAutoForegroundColAct(self):
        self.updateAutoForegroundCol(self._rightClickHeaderCol)

    def _wordStatsAct(self):
        colName = self.horizontalHeaderItem(self._rightClickHeaderCol).text()

        # get strings
        data = []
        for col in range(self.columnCount()):
            if self.horizontalHeaderItem(col).text() != colName: continue

            for row in range(self.rowCount()):
                value = None
                try:
                    item = self.item(row, col)
                    value = item.data(self._role)
                    value = float(value)
                except Exception as ex:
                    # string
                    if value and isinstance(value, str):
                        data.append(value)
            break # only process the first matched column name

        if not data: return

        # count
        wordStats = {}
        for string in data:
            strings_ = re.split(',|，|、|。|;|；', string) # no '.' because like '工业4.0'
            strings = []
            for string in strings_:
                string = string.strip()
                if not string: continue

                if string[-1] == ')' or string[-1] == '）': # remove string like '(一)'
                    string = string[:-3]

                strings.append(string)

            for string in strings:
                wordStats.setdefault(string, 0)
                wordStats[string] += 1

        # generate DF
        df = pd.DataFrame(wordStats, index=['计数']).T
        df.sort_values('计数', ascending=False, inplace=True)

        count = df['计数']
        sum = count.sum()
        df['占比词汇(%)'] = count*100/sum
        df['占比行(%)'] = count*100/len(data)

        DyDataFrameWindow('词汇统计-{0}, 总共{1}个'.format(colName, df.shape[0]), df, self)

    def _probDistAct(self):
        # If column name is totally not related with numbers, ignore
        colName = self.horizontalHeaderItem(self._rightClickHeaderCol).text()
        if self._isNonNbrColName(colName): return

        series = self.getNumberSeries(colName)
        if series is None: return

        DyMatplotlib.newFig()

        series.hist(bins=100, alpha=0.5, color='r')
        plt.title(colName)
        plt.gcf().show()

    def _describeAct(self):
        df = self.getNumberDataFrame()
        if df is None: return

        info = df.describe()

        DyDataFrameWindow('描述统计', info, self)

    def _scatterMatrixAct(self):
        df = self.getNumberDataFrame()
        if df is None: return

        DyMatplotlib.newFig()

        pd.scatter_matrix(df)
        plt.gcf().show()

    def getNumberDataFrame(self):
        """
            get number DataFrame
        """
        # get columns data
        data = {}
        columns = []
        for col in range(self.columnCount()):
            # only get columns with number
            colName = self.horizontalHeaderItem(col).text()
            if self._isNonNbrColName(colName):
                continue

            colData = []
            for row in range(self.rowCount()):
                try:
                    item = self.item(row, col)
                    value = item.data(self._role)
                    value = float(value)
                except Exception as ex:
                    value = None

                colData.append(value)

            if colData:
                columns.append(colName)
                data[colName] = colData
        
        # add columns only for same sequence as in table view
        return pd.DataFrame(data, columns=columns) if data else None

    def getNumberSeries(self, colName):
        """ get number series for specified column name """
        data = []

        # get column postion
        for col in range(self.columnCount()):
            if self.horizontalHeaderItem(col).text() == colName:
                # get series data
                for row in range(self.rowCount()):
                    try:
                        item = self.item(row, col)
                        value = item.data(self._role)
                        value = float(value)
                    except Exception as ex:
                        continue

                    data.append(value)

        return pd.Series(data, name = colName) if data else None

    def getNumberColNames(self):
        """ get number column names """

        colNames = []
        for col in range(self.columnCount()):
            headerItem = self.horizontalHeaderItem(col)
            colName = headerItem.text()
            if self._isNonNbrColName(colName): continue

            colNames.append(colName)

        return colNames if colNames else None

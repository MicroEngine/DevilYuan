from datetime import *

from DyCommon.DyCommon import *


class DyStockDataTradeDayTable:

    # table format
    # {year:{month:{day:[bool,index to compact table]}}}

    # compact table format
    # [date]

    def __init__(self, mongoDbEngine, gateway, info):
        self._mongoDbEngine = mongoDbEngine
        self._gateway = gateway
        self._info = info

        self._init()

    def _init(self):
        self._table = {}
        self._compactTable = []

    def _buildIndex(self, date):
        year, month, day = date.split('-')

        i = 0
        while i < len(self._compactTable):
            tradeDay = self._compactTable[i]
            if date < tradeDay: break
            i += 1

        self._table[year][month][day][1] = i - 1

    def _updateIndex(self):
        self._compactTable.sort()

        preDate = None
        oldest = None
        date = None # will be latest after loop

        years = sorted(self._table)
        for year in years:
            months = sorted(self._table[year])
            for month in months:
                days = sorted(self._table[year][month])
                for day in days:
                    date = year + '-' + month + '-' + day

                    if not oldest: oldest = date

                    # index should be built based on continous days
                    if preDate:
                        if DyTime.getDateStr(preDate, 1) != date:
                            self._info.print("Days in TradeDay Table aren't continous!", DyLogData.error)
                            return False
                    preDate = date

                    # build index for day
                    self._buildIndex(date)

        return True

    def _convertTradeDays(self, tradeDays):
        tradeDays = [doc['datetime'].strftime("%Y-%m-%d") for doc in tradeDays]

        tradeDays.sort()

        return tradeDays

    def _load3(self, startDate, endDate, n):
        # 分部分载入
        # front part
        startDateNew, endDateNew = startDate, endDate
        if isinstance(startDate, int):
            startDateNew, endDateNew = endDateNew, startDateNew

        frontStartDate, frontEndDate, frontTradeDays = self._load2(startDateNew, endDateNew)
        if frontStartDate is None: return None, None, None

        # back part
        backStartDate, backEndDate, backTradeDays = self._load2(endDate, n)
        if backStartDate is None: return None, None, None

        # combine trade days, always zero offset trade day is duplicated
        for day in frontTradeDays:
            if day in backTradeDays:
                backTradeDays.remove(day)

        tradeDays = frontTradeDays + backTradeDays
        tradeDays.sort()

        # combine date range
        if frontStartDate < backStartDate:
            startDate = frontStartDate
        else:
            startDate = backStartDate

        if backEndDate > frontEndDate:
            endDate = backEndDate
        else:
            endDate = frontEndDate

        # combine with trade days
        startDateNew = tradeDays[0]
        endDateNew = tradeDays[-1]

        if startDate < startDateNew:
            startDateNew = startDate

        if endDate > endDateNew:
            endDateNew = endDate

        return  startDateNew, endDateNew, tradeDays

    def _load2(self, startDate, endDate):
        if isinstance(endDate, int):
            tradeDays = self._mongoDbEngine.getTradeDaysByRelative(startDate, endDate)
            if tradeDays is None: return None, None, None

            assert(tradeDays)

            tradeDays = self._convertTradeDays(tradeDays)

            startDateNew = tradeDays[0]
            endDateNew = tradeDays[-1]

            if startDate > endDateNew:
                endDateNew = startDate

            elif startDate < startDateNew:
                startDateNew = startDate

            return  startDateNew, endDateNew, tradeDays

        else:
            tradeDays = self._mongoDbEngine.getTradeDaysByAbsolute(startDate, endDate)
            if tradeDays is None: return None, None, None

            tradeDays = self._convertTradeDays(tradeDays)

            return  startDate, endDate, tradeDays

    def load(self, dates):
        self._info.print("开始载入交易日数据{0}...".format(dates))

        # 初始化
        self._init()

        # 根据不同格式载入
        if len(dates) == 2:
            startDate, endDate, tradeDays = self._load2(dates[0], dates[1])
        else:
            startDate, endDate, tradeDays = self._load3(dates[0], dates[1], dates[2])

        if startDate is None:
            return False

        if not self._set2Table(startDate, endDate, tradeDays):
            return False

        self._info.print("交易日数据[{0}, {1}]载入完成".format(startDate, endDate))

        return True

    def tLatestDay(self):
        return self._compactTable[-1] if self._compactTable else None

    def tOldestDay(self):
        return self._compactTable[0] if self._compactTable else None

    def tDaysOffset(self, base, n):
        if isinstance(base, datetime):
            base = base.strftime("%Y-%m-%d")

        base = base.split('-')

        try:
            index = self._table[base[0]][base[1]][base[2]][1]
        except Exception as ex:
            pass
        else:
            # find it
            nIndex = index + n
            if nIndex >= 0 and nIndex < len(self._compactTable):
                return self._compactTable[nIndex]

        return None

    def isIn(self, start, end):
        dates = DyTime.getDates(start, end)

        for date in dates:
            date = date.strftime("%Y-%m-%d").split('-')
            if date[0] not in self._table:
                return False
            if date[1] not in self._table[date[0]]:
                return False
            if date[2] not in self._table[date[0]][date[1]]:
                return False

        return True

    def get(self, start, end):
        """ @return: [trade day] """

        dates = DyTime.getDates(start, end)

        tradeDays = []
        for date in dates:
            dateSave = date.strftime("%Y-%m-%d")
            date = dateSave.split('-')
            if date[0] in self._table:
                if date[1] in self._table[date[0]]:
                    if date[2] in self._table[date[0]][date[1]]:
                        if self._table[date[0]][date[1]][date[2]][0]:
                            tradeDays.append(dateSave)

        return tradeDays

    def _update2Db(self, startDate, endDate, tradeDays):

        # convert to MongoDB format
        datesForDb = []
        dates = DyTime.getDates(startDate, endDate)

        for date in dates:
            doc = {'datetime':date}

            if date.strftime('%Y-%m-%d') in tradeDays:
                doc['tradeDay'] = True
            else:
                doc['tradeDay'] = False

            datesForDb.append(doc)

        # update into DB
        return self._mongoDbEngine.updateTradeDays(datesForDb)

    def _set(self, startDate, endDate, tradeDays):
        return self._set2Table(startDate, endDate, tradeDays) and self._update2Db(startDate, endDate, tradeDays)

    def _set2Table(self, start, end, tradeDays):
        """ [@start, @end] is range """

        dates = DyTime.getDates(start, end)

        dates = [x.strftime("%Y-%m-%d")  for x in dates]
        days = tradeDays

        for day in dates:
            dayTemp = day.split('-')

            if dayTemp[0] not in self._table:
                self._table[dayTemp[0]] = {}

            if dayTemp[1] not in self._table[dayTemp[0]]:
                self._table[dayTemp[0]][dayTemp[1]] = {}

            if day in days:
                self._table[dayTemp[0]][dayTemp[1]][dayTemp[2]] = [True, -1]
            else:
                self._table[dayTemp[0]][dayTemp[1]][dayTemp[2]] = [False, -1]

        self._compactTable.extend(days)

        return self._updateIndex()

    def update(self, startDate, endDate):
        self._info.print('开始更新交易日数据...')

        if self.load([startDate, endDate]):
            self._info.print('交易日数据已在数据库')
            return True

        tradeDays = self._gateway.getTradeDays(startDate, endDate)
        if tradeDays is None: return False

        # set to tables and then update to DB
        if not self._set(startDate, endDate, tradeDays):
            return False

        self._info.print('交易日数据更新完成')
        return True

    def getLatestDateInDb(self):
        date = self._mongoDbEngine.getDaysLatestDate()
        if date is None: return None

        return date['datetime'].strftime("%Y-%m-%d")

    def getLatestTradeDayInDb(self):
        date = self._mongoDbEngine.getDaysLatestTradeDay()
        if date is None: return None

        return date['datetime'].strftime("%Y-%m-%d")

    def tDaysOffsetInDb(self, base, n=0):
        startDate, endDate, tradeDays = self._load2(base, n)
        if startDate is None: return None

        if n <= 0:
            n -= 1

        try:
            day = tradeDays[n]
        except Exception as ex:
            day = None

        return day

    def tDaysCountInDb(self, startDate=None, endDate=None):
        """
            从数据库获取指定日期范围的交易日数
        """
        tradeDays = self._mongoDbEngine.getTradeDaysByAbsolute(startDate, endDate)
        if tradeDays is None:
            return None

        return len(tradeDays)

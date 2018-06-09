import json
import re
import requests
from bs4 import BeautifulSoup

from DyCommon.DyCommon import *


class DyStockDataSpider(object):
    """
        股票数据爬虫
    """
    dy2JqkaMap = {'营业收入YoY(%)': '营业总收入同比增长率',
                  '净利润YoY(%)': '净利润同比增长率',
                  '每股收益(元)': '基本每股收益',
                  '每股现金流(元)': '每股经营现金流'
                 }

    def _dy2Jqka(indicators):
        return [DyStockDataSpider.dy2JqkaMap[x] for x in indicators]

    def _getShareQuantity(strQuantity):
        """
            @strQuantity: str, like '45.22万股', '1.02亿股' or '234.44'
            @return: float, 单位是万股
        """
        quantity = DyCommon.toFloat(re.findall(r"\d*\.?\d+", strQuantity)[0])
        if '亿' in strQuantity:
            quantity *= 10000

        return quantity

    def getLatestFinanceReport(code, indicators):
        """
            从财务报表获取指定指标最新值
            @indicators: [DevilYuan财务指标]
            @return: [value]
        """
        indicators = DyStockDataSpider._dy2Jqka(indicators)

        mainLink = 'http://basic.10jqka.com.cn/{0}/flash/main.txt'.format(code[:-3])
        r = requests.get(mainLink)

        table = dict(json.loads(r.text))

        values = []
        for indicator in indicators:
            # get @indicator position
            pos = None
            for i, e in enumerate(table['title']):
                if isinstance(e, list):
                    if e[0] == indicator:
                        pos = i
                        break

            # 指标最近的值
            value = DyCommon.toFloat(table['report'][pos][0], None)
            values.append(value)

        return values

    def getLatestFundPositionsRatio(code):
        """
            最近机构持股占比流通股比例总和
            @return: ratio(%), fundNbr
        """
        mainLink = 'http://basic.10jqka.com.cn/16/{0}/position.html'.format(code[:-3])
        r = requests.get(mainLink)
        soup = BeautifulSoup(r.text, 'lxml')

        sumRatio = 0
        fundNbr = 0

        try:
            tag = soup.find('h2', text='机构持股明细')
            tag = tag.parent.parent.find('th', text='占流通股比例')
            tag = tag.parent.parent.parent.find('tbody')
            tags = tag.find_all('tr')
            
            for tag in tags:
                tags_ = tag.find_all('td')
                sumRatio += DyCommon.toFloat(tags_[3].string[:-1]) # '占流通股比例'

                fundNbr += 1

        except Exception as ex:
            pass
            
        return sumRatio, fundNbr

    def getLatestRealFreeShares(code):
        """
            最近实际流通A股数（亿），主要是统计机构持有的流通股数
            由于'股份类型'可能会是A股，H股和B股的组合，所以有可能得到的实际流通A股数会多于返回值。
            @return: 多少亿A股, 类型。类型 - 'A股', 'B股', 'H股'的组合, 比如 'A股B股'，一旦含有非A股，意味着实际流通A股数会多于返回值。一般误差不大，可以接受。
        """
        # 股东研究
        mainLink = 'http://basic.10jqka.com.cn/16/{0}/holder.html'.format(code[:-3])
        r = requests.get(mainLink)
        soup = BeautifulSoup(r.text, 'lxml')

        try:
            lockedShares = 0 # 锁定股票数（万股）
            lockedShareType = ''

            tag = soup.find('span', text='十大流通股东')
            tag = tag.parent.parent.parent.find('th', text='机构或基金名称')
            table = tag.parent.parent.parent

            # check if '机构成本估算(元)' existing
            tag = table.find('thead')
            tag = table.find(text='机构成本估算(元)')
            costCol, typePos = (False, 4) if tag is None else (True, 5)
            
            tag = table.find('tbody')
            tags = tag.find_all('tr')
            for tag in tags:
                tags_ = tag.find_all('td')

                if costCol:
                    cost = DyCommon.toFloat(tags_[3].string, None) # 机构成本估算(元)
                else:
                    cost = None

                if cost is None: # 没有成本，可以认为是原始股东或者大散户
                    # !!!持有数量格式为'450.76万股'，格式跟以前不一样
                    lockedShares += DyStockDataSpider._getShareQuantity(tags_[0].string)

                    types = str(tags_[typePos].string).split(',')
                    for type in types:
                        if type[2:] not in lockedShareType:
                            lockedShareType += type[2:]

            # 股本结构
            mainLink = 'http://basic.10jqka.com.cn/16/{0}/equity.html'.format(code[:-3])
            r = requests.get(mainLink)
            soup = BeautifulSoup(r.text, 'lxml')

            tag = soup.find('span', text='总股本')
            tag = tag.parent.parent.parent.find('span', text='流通A股')
            tag = tag.parent.parent.find('td')
            freeShares = DyStockDataSpider._getShareQuantity(tag.string)

        except Exception: # 新股可能没有十大流通股东数据
            # 股本结构
            mainLink = 'http://basic.10jqka.com.cn/16/{0}/equity.html'.format(code[:-3])
            r = requests.get(mainLink)
            soup = BeautifulSoup(r.text, 'lxml')

            tag = soup.find('h2', text='A股结构图')
            tag = tag.parent.parent.find(text='流通A股') # seems tag.parent.parent.find('th', text='流通A股') not working???
            tag = tag.parent.parent.find('td')
            freeShares = DyStockDataSpider._getShareQuantity(tag.string)

            lockedShares = 0
            lockedShareType = 'A股'

        # return
        realFreeShares = (freeShares - lockedShares)/10000
        return realFreeShares, lockedShareType

    def getCompanyInfo(code, indicators):
        colNames = ['所属行业', '主营业务', '涉及概念']

        # filter
        newColNames = []
        for name in colNames:
            if name in indicators:
                newColNames.append(name)

        newColData = [None]*len(newColNames)

        try:
            r = requests.get('http://basic.10jqka.com.cn/16/{0}/'.format(code[:-3]))

            soup = BeautifulSoup(r.text, 'lxml')

            tag = soup.find('h2', text='公司概要')
            companyOutline = tag.parent.parent

            # 所属行业
            if '所属行业' in newColNames:
                tag = companyOutline.find('span', text='所属行业：')
                content = str(tag.next_sibling.next_sibling.string)

                newColData[newColNames.index('所属行业')] = content

            # 主营业务
            if '主营业务' in newColNames:
                tag = companyOutline.find('span', text='主营业务：')
                tr = tag.parent.parent
                tag = tr.find('a')
                content = str(tag.string)

                newColData[newColNames.index('主营业务')] = content

            # 涉及概念
            if '涉及概念' in newColNames:
                tag = companyOutline.find('div', text='概念强弱排名：')
                if tag is None:
                    tag = companyOutline.find('span', text='涉及概念：')

                tag = tag.next_sibling.next_sibling
                tags = tag.find_all('a')
                contents = []
                for tag in tags:
                    content = tag.contents[0]
                    if content == '详情>>': continue

                    if tag.has_attr('title'):
                        rank = tag['title'][-1]
                        content += '(' + rank + ')'
        
                    contents.append(content)

                newColData[newColNames.index('涉及概念')] = ','.join(contents)

        except Exception as ex:
            pass

        return newColNames, newColData
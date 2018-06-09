import asyncio
import aiohttp
from bs4 import BeautifulSoup

from EventEngine.DyEvent import *
from ..DyStockTradeCommon import *
from DyCommon.DyCommon import *


class DyStockTradeStrategyGatewayEngine(object):
    """ 策略实盘时抓取网络数据引擎 """

    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._registerEvent()

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockCompanyInfoReq, self._stockCompanyInfoReqHandler, DyStockTradeEventHandType.gatewayEngine)

    @asyncio.coroutine
    def _asyncGetOneCompanyInfo(self, code, indicators):
        colNames = ['所属行业', '主营业务', '涉及概念']

        # filter
        newColNames = []
        for name in colNames:
            if name in indicators:
                newColNames.append(name)

        newColData = [None]*len(newColNames)

        session = aiohttp.ClientSession()

        try:
            r = yield from session.get('http://basic.10jqka.com.cn/16/{0}/'.format(code[:-3]))
            text = yield from r.text()

            soup = BeautifulSoup(text, 'lxml')

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
                    tag = tr.find('span', text='涉及概念：')

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

    @asyncio.coroutine
    def _getOneCompanyInfo(self, code, indicators):
        r = yield from self._asyncGetOneCompanyInfo(code, indicators)

        _, data = r
        if data[0] is None:
            return None

        return {code: data} # data is ['所属行业', '涉及概念']

    def _getCompanyInfo(self, codes, indicators):
        """
            @return: {code: ['所属行业', '涉及概念']}, '涉及概念'的格式是以,分开的字符串
        """
        # async run
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # coroutines
        coroutines = []
        for code in codes:
            coroutine = self._getOneCompanyInfo(code, indicators)
            coroutines.append(coroutine)

        # run
        try:
            res = loop.run_until_complete(asyncio.gather(*coroutines))
        except Exception as ex:
            self._info.print("获取股票公司信息异常: {0}".format(repr(ex)), DyLogData.error)
            return None

        # format return results
        retData = {}
        for data in res:
            if data is None:
                continue

            retData.update(data)

        return retData if retData else None

    def _stockCompanyInfoReqHandler(self, event):
        # unpack
        codes = event.data['codes']
        indicators = event.data['indicators'] # ['所属行业', '涉及概念']

        # sync get from network
        ret = self._getCompanyInfo(codes, indicators)
        if ret is None:
            return

        # put event
        event = DyEvent(DyEventType.stockCompanyInfoAck)
        event.data = ret # event.data is {code: ['所属行业', '涉及概念']}

        self._eventEngine.put(event)
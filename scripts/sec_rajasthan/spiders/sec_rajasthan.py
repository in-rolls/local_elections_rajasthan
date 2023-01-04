# -*- coding: utf-8 -*-

import os
import gzip
import pandas as pd

import scrapy
from scrapy.http import FormRequest

from ..items import (ContestingSarpanchItem, StatsNominationItem, WinnerSarpanchItem, WarnWinningPanchItem)

import requests


class SecRajasthanSpider(scrapy.Spider):
    #download_delay = 1
    name = 'sec_rajasthan'
    allowed_domains = ['sec.rajasthan.gov.in']
    start_urls = ['https://sec.rajasthan.gov.in/grampanchayatdetails.aspx']

    def download_file(self, url, local_filename):
        # NOTE the stream=True parameter below
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    #if chunk: 
                    f.write(chunk)
        return local_filename

    def save_gzip_file(self, response, filename):
        fn = filename + '.gz'
        with gzip.open(fn, 'wb') as f:
            f.write(response.body)
        self.logger.info('Saved file {}'.format(fn) )
        return fn

    def parse(self, response):
        # Parse Districts from Image Map
        """
            How to pass argument to spider:-
            arg = getattr(self, 'arg', None)

            Command line:-
            scrapy crawl myspider -a arg=foo
        """
        if not os.path.exists('./pdf'):
            os.makedirs('./pdf')

        districts = getattr(self, 'districts', None)
        if districts:
            self.dist_list = [a.strip().upper() for a in districts.split(',')]
        else:
            self.dist_list = []

        self.logger.info('Arguments: districts={!s}'.format(districts))

        item = {}

        options = response.xpath("//select[@id='ContentPlaceHolder1_DropDownListElection']/option")
        for o in options:
            val = o.attrib['value']
            item['ElectionType'] = o.xpath('.//text()').extract()[0]
            target = 'ctl00$ContentPlaceHolder1$DropDownListElection'
            arg = ''
            yield FormRequest.from_response(response,
                formdata={'__EVENTTARGET': target, '__EVENTARGUMENT': arg,
                'ctl00$ContentPlaceHolder1$DropDownListElection': val},
                callback = self.parse_election_duration,
                dont_click = True,
                dont_filter = True,
                meta={'item': item.copy()})

    def parse_election_duration(self, response):
        self.logger.info('Parse Election Duration %s (meta=%r)' % (response.url, response.meta))
        options = response.xpath("//select[@id='ContentPlaceHolder1_DropDownListPeriod']/option")
        for o in options:
            val = o.attrib['value']
            item = response.meta['item']
            item['ElectionDuration'] = o.xpath('.//text()').extract()[0]
            target = 'ctl00$ContentPlaceHolder1$DropDownListPeriod'
            arg = ''
            yield FormRequest.from_response(response,
                formdata={'__EVENTTARGET': target, '__EVENTARGUMENT': arg,
                'ctl00$ContentPlaceHolder1$DropDownListPeriod': val},
                callback = self.parse_district,
                dont_click = True,
                dont_filter = True,
                meta={'item': item.copy()})

    def parse_district(self, response):
        # Parse District
        self.logger.info('Parse District URL %s (meta=%r)' % (response.url, response.meta))
        options = response.xpath("//select[@id='ContentPlaceHolder1_DistrictDropDownList']/option")
        for o in options:
            text = o.xpath('.//text()').extract()[0]
            val = o.attrib['value']
            item = response.meta['item']
            item['District'] = text
            if len(self.dist_list) > 0 and (text not in self.dist_list):
                continue
            target = 'ctl00$ContentPlaceHolder1$PanchayatSamitiDropDownList'
            arg = ''
            yield FormRequest.from_response(response,
                formdata={'__EVENTTARGET': target, '__EVENTARGUMENT': arg,
                'ctl00$ContentPlaceHolder1$DistrictDropDownList': val},
                callback = self.parse_panchayat,
                dont_click = True,
                dont_filter = True,
                meta={'item': item.copy()})

    def parse_panchayat(self, response):
        self.logger.info('Parse Panchayat URL %s (meta=%r)' % (response.url, response.meta))
        options = response.xpath("//select[@id='PanchayatSamitiDropDownList']/option")
        for o in options:
            val = o.attrib['value']
            text = o.xpath('.//text()').extract()[0]
            item = response.meta['item']
            item['PanchayatSamiti'] = text
            target = 'ctl00$ContentPlaceHolder1$PanchayatSamitiDropDownList'
            arg = ''
            yield FormRequest.from_response(response,
                formdata={'__EVENTTARGET': target, '__EVENTARGUMENT': arg,
                'ctl00$ContentPlaceHolder1$PanchayatSamitiDropDownList': val
                },
                callback = self.parse_submit,
                dont_click = True,
                dont_filter = True,
                meta={'item': item.copy()})

    def parse_submit(self, response):
        self.logger.info('Parse Submit URL %s (meta=%r)' % (response.url, response.meta))
        item = response.meta['item']
        target = ''
        arg = ''
        yield FormRequest.from_response(response,
            formdata={'__EVENTTARGET': target, '__EVENTARGUMENT': arg,
            'ctl00$ContentPlaceHolder1$btnSubmit': 'Submit'},
            callback = self.parse_table,
            dont_click = True,
            dont_filter = True,
            meta={'item': item.copy()})

    def parse_table(self, response):
        items = []
        self.logger.info('Parse Table URL %s (meta=%r)' % (response.url, response.meta))
        item = response.meta['item']
        tab1 = response.xpath("//div[@id='tabs-1']//table[1]").extract()
        if len(tab1):
            dfs = pd.read_html(tab1[0])
            df = dfs[0]
            for i, r in df.iterrows():
                x = ContestingSarpanchItem()
                x['ElectionType'] = item['ElectionType']
                x['ElectionDuration'] = item['ElectionDuration']
                x['District'] = item['District']
                x['PanchayatSamiti'] = item['PanchayatSamiti']
                x['SrNo'] = r[0]
                x['NameOfGramPanchayat'] = r[1]
                x['CategoryOfGramPanchayat'] = r[2]
                x['ContestingCandidateSerialNo'] = r[3]
                x['NameOfContestingCandidate'] = r[4]
                x['FatherHusbandOfContestingCandidate'] = r[5]
                x['Gender'] = r[6]
                x['MartialStatus'] = r[7]
                x['CategoryOfCandidate'] = r[8]
                x['EducationStatus'] = r[9]
                x['ContestingCandidateOccupation'] = r[10]
                x['Age'] = r[11]
                x['TotalValueOfCapitalAssets'] = r[12]
                x['ChildrenBefore27111995'] = r[13]
                x['ChildrenOnOrAfter28111995'] = r[14]
                x['MobileNo'] = r[15]
                x['EmailAddress'] = r[16]
                items.append(x)

        tab3 = response.xpath("//div[@id='tabs-3']//table[1]").extract()
        if len(tab3):
            dfs = pd.read_html(tab3[0])
            df = dfs[0]
            for i, r in df.iterrows():
                if i == (len(df) - 1):
                    break
                x = StatsNominationItem()
                x['ElectionType'] = item['ElectionType']
                x['ElectionDuration'] = item['ElectionDuration']
                x['District'] = item['District']
                x['PanchayatSamiti'] = item['PanchayatSamiti']
                x['SrNo'] = r[0]
                x['GramPanchayat'] = r[1]
                x['NominationTotalNoOfNominationFilled'] = r[2]
                x['NominationCandidate'] = r[3]
                x['ValidlyNominatedCandidate'] = r[4]
                x['Withdrawal'] = r[5]
                x['Unopposed'] = r[6]
                x['Contestants'] = r[7]
                items.append(x)

        links = response.xpath("//a[starts-with(@id, 'ContentPlaceHolder1_Repeater4_DownloadButton_')]")
        pdfs = []
        urls = []
        for l in links:
            url = 'https://sec.rajasthan.gov.in' + l.attrib['href']
            fn = url.split('/')[-1]
            pdfs.append(fn)
            urls.append(url)
            #self.download_file(url, os.path.join('./pdf', fn))

        tab4 = response.xpath("//div[@id='tabs-4']//table[1]").extract()
        if len(tab4):
            dfs = pd.read_html(tab4[0])
            df = dfs[0]
            for i, r in df.iterrows():
                x = WinnerSarpanchItem()
                x['ElectionType'] = item['ElectionType']
                x['ElectionDuration'] = item['ElectionDuration']
                x['District'] = item['District']
                x['PanchayatSamiti'] = item['PanchayatSamiti']
                x['SrNo'] = r[0]
                x['NameOfGramPanchyat'] = r[1]
                x['CategoryOfGramPanchyat'] = r[2]
                x['TotalNoOfContestingCandidate'] = r[3]
                x['ElectedUnoppose'] = r[4]
                x['TotalElectorateVotes'] = r[5]
                x['TotalPolledVotes'] = r[6]
                x['RejectedVotes'] = r[7]
                x['TotalValidVotes'] = r[8]
                x['PollPercent'] = r[9]
                x['WinnerCandidateName'] = r[10]
                x['ViewPledge'] = urls[i] # pdfs[i] # r[11]
                x['VoteSecureByWinner'] = r[12]
                x['RunnerupCandidateName'] = r[13]
                x['VoteSecureByRunnerup'] = r[14]
                x['TotalNoOfNOTACount'] = r[15]
                x['TenderedVotes'] = r[16]
                items.append(x)

        tab7 = response.xpath("//div[@id='tabs-7']//table[1]").extract()
        if len(tab7):
            dfs = pd.read_html(tab7[0])
            df = dfs[0]
            for i, r in df.iterrows():
                x = WarnWinningPanchItem()
                x['ElectionType'] = item['ElectionType']
                x['ElectionDuration'] = item['ElectionDuration']
                x['District'] = item['District']
                x['PanchayatSamiti'] = item['PanchayatSamiti']
                x['SrNo'] = r[0]
                x['Grampanchayat'] = r[1]
                x['WardNo'] = r[2]
                x['NameOfVillage'] = r[3]
                x['CategoryOfWard'] = r[4]
                x['NameOfCandidate'] = r[5]
                x['TotalNoOfVotes'] = r[6]
                x['VotesPolled'] = r[7]
                x['PollPercent'] = r[8]
                x['WhetherElectedUnoppose'] = r[9]
                x['CategoryOfWinningCandidate'] = r[10]
                x['RemarkIfAny'] = r[11]
                x['WinnerVotes'] = r[12]
                x['LooserVotes'] = r[13]
                items.append(x)
        for i in items:
            yield i

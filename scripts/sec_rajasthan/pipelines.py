# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import gzip
from scrapy.exporters import CsvItemExporter
from scrapy import signals
from pydispatch import dispatcher
from .items import (ContestingSarpanchItem, StatsNominationItem, WinnerSarpanchItem, WarnWinningPanchItem)

def item_type(item):
    return type(item).__name__.replace('Item','') # TeamItem => team

class SecRajasthanPipeline(object):
    SaveTypes = ['ContestingSarpanch', 'StatsNomination', 'WinnerSarpanch', 'WarnWinningPanch']

    def __init__(self):
        dispatcher.connect(self.spider_opened, signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)

    def spider_opened(self, spider):
        self.files = dict([ (name, gzip.open(name+'.csv.gz','w+b')) for name in self.SaveTypes ])
        self.exporters = dict([ (name,CsvItemExporter(self.files[name])) for name in self.SaveTypes])
        self.exporters['ContestingSarpanch'].fields_to_export = ContestingSarpanchItem.fields_to_export
        self.exporters['StatsNomination'].fields_to_export = StatsNominationItem.fields_to_export
        self.exporters['WinnerSarpanch'].fields_to_export = WinnerSarpanchItem.fields_to_export
        self.exporters['WarnWinningPanch'].fields_to_export = WarnWinningPanchItem.fields_to_export
        [e.start_exporting() for e in self.exporters.values()]

    def spider_closed(self, spider):
        [e.finish_exporting() for e in self.exporters.values()]
        [f.close() for f in self.files.values()]

    def process_item(self, item, spider):
        what = item_type(item)
        if what in set(self.SaveTypes):
            self.exporters[what].export_item(item)
        return item

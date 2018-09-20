from pymongo import MongoClient
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# import seaborn as sns
import datetime

from utils.constants import *


class Mongo_db(object):
    def __init__(self):
        self.dbClient = MongoClient('localhost', 27017)
        # self.today = datetime.datetime.now().strftime('%Y%m%d')
        self.today = datetime.datetime.now()

    def dbInsert(self, dbName, collectionName, d):
        """向MongoDB中插入数据，d是具体数据"""
        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.insert_one(d)

    # ----------------------------------------------------------------------
    def dbQuery(self, dbName, collectionName, d, sortKey='', sortDirection=ASCENDING):

        """从MongoDB中读取数据，d是查询要求，返回的是数据库查询的指针"""

        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]

            if sortKey:
                cursor = collection.find(d).sort(sortKey, sortDirection)  # 对查询出来的数据进行排序
            else:
                cursor = collection.find(d)

            if cursor:
                return list(cursor)
            else:
                return []
            # else:
            #     self.writeLog(text.DATA_QUERY_FAILED)
            return []

    # ----------------------------------------------------------------------
    def dbUpdate(self, dbName, collectionName, d, flt, upsert=False):

        """向MongoDB中更新数据，d是具体数据，flt是过滤条件，upsert代表若无是否要插入"""

        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.replace_one(flt, d, upsert)
        # else:
        #     self.writeLog(text.DATA_UPDATE_FAILED)

        # ----------------------------------------------------------------------

    def dbDelete(self, dbName, collectionName, flt):

        """从数据库中删除数据，flt是过滤条件"""

        if self.dbClient:
            db = self.dbClient[dbName]
            collection = db[collectionName]
            collection.delete_one(flt)
        # else:
        #     self.writeLog(text.DATA_DELETE_FAILED)

        # ----------------------------------------------------------------------

    def loadTick(self, dbName, collectionName, days):
        """从数据库中读取Tick数据，startDate是datetime对象"""
        startDate = self.today - datetime.timedelta(days)

        d = {'datetime': {'$gte': startDate}}
        tickData = self.dbQuery(dbName, collectionName, d, 'datetime')
        res = pd.DataFrame(tickData)
        return res


if __name__ == '__main__':
    m = Mongo_db()
    dbName = 'VnTrader_Tick_Db'
    collectionName = 'rb1901'
    d = m.loadTick(dbName, collectionName, 1)
    d = d.set_index('time').sort_index()
    d['diffvol'] = d['bidVolume1'] - d['askVolume1']
    d['latevol'] = d['volume'].diff()
    #   挂单成交异常

    buy = d[(d['diffvol'] > d['diffvol'].quantile(0.999)) & (d['latevol'] > d['diffvol'].quantile(0.999))]
    sell = d[(d['diffvol'] < d['diffvol'].quantile(0.001)) & (d['latevol'] > d['diffvol'].quantile(0.999))]

    d['diffvol'].plot()
    plt.show()
    d
    d

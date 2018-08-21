#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
import scipy as sp
import tushare as ts
from opendatatools import swindex

from dataProvider.trading_calendar import *
from utils.constants import *
from utils.tool import *


class DataApi(object):
    def __init__(self):
        ts.set_token('0503684c1ca87a31116049960065adbf985e0c052adb268a2b5397dd')
        self.pro = ts.pro_api()
        self.today = datetime.datetime.now().strftime('%Y%m%d')
        self.dataProvider_dir = os.path.dirname(__file__)
        log_name = os.path.join(self.dataProvider_dir, "log_dir/analysis_%s.log" % self.today)
        get_logger(log_name)

    def trading_day(self, start_date='', end_date=''):
        res = self.pro.trade_cal(exchange_id='SSE', start_date=start_date, end_date=end_date, is_open='1')[
            'cal_date'].tolist()
        return res

    def delete_quote(self, dir=None):
        # 每日重新更新行情缓存
        if dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), "cache/")
            f_list = os.listdir(cache_dir)
            #   删除所有csv的缓存文件
            for fileNAME in f_list:
                if os.path.splitext(fileNAME)[1] == '.csv':
                    os.remove(os.path.join(cache_dir, fileNAME))
            logging.info('remove all csv')
        else:
            os.remove(os.path.join(self.dataProvider_dir, dir))
            logging.info('remove %s', dir)

    def index_weight(self, index_code=None):
        #   输入列表['000300.SH','399905.SZ','000016.SH']获取对应指数成分股
        hs300 = ts.get_hs300s()
        zz500 = ts.get_zz500s()
        sz50 = ts.get_sz50s()
        hs300['index_code'] = '000300.SH'
        zz500['index_code'] = '399905.SZ'
        sz50['index_code'] = '000016.SH'
        # 汇总数据
        res = pd.concat([hs300, zz500, sz50], ignore_index=True)
        #   标准化code
        res['code'] = [i + '.SH' if i[0] == '6' else i + '.SZ' for i in res['code']]
        if index_code is None:
            index_code = ['000300.SH', '399905.SZ', '000016.SH']
        res = res[res['index_code'].isin(index_code)]
        return res

    def stock_bar(self, code=None, start_date=None, end_date=None, field='daily'):
        #   如不输入code则返回所有股票行情，不输入起始时间则返回前一交易日行情
        current_dir = 'cache\stock_' + field + '.csv'
        data_file_path = os.path.join(self.dataProvider_dir, current_dir)
        lastTradingDay = get_pre_trading_day()
        if start_date is None:
            start_date = lastTradingDay
        if end_date is None or end_date >= lastTradingDay:
            end_date = lastTradingDay
        try:
            data = pd.read_csv(data_file_path, converters={'trade_date': str})
            if 'Unnamed: 0' in data.columns:
                del data['Unnamed: 0']
            if data['trade_date'].min() > lastTradingDay:
                self.delete_quote(current_dir)
        except Exception as e:
            data = None
        if data is None:
            data = pd.DataFrame()
            #   每20天分段取数据
            betweenDay = 1
            trading_day_list = get_trading_day_range(MIN_BEGIN_DAY, lastTradingDay)[1:]
            for month in range(len(trading_day_list))[::betweenDay]:
                datelist = trading_day_list[month:month + betweenDay]
                # temp = da.pro.daily(start_date=datelist[0], end_day=datelist[-1])
                temp = da.pro.query(field, trade_date=datelist[0])
                data = data.append(temp, ignore_index=True)
                logging.info('stock_%s:%s') % (field, datelist[0])
            data = data.drop_duplicates(['ts_code', 'trade_date'])
            if not data.empty:
                data.to_csv(data_file_path)
        else:
            max_day = str(data['trade_date'].max())
            if max_day < end_date:
                betweenDay = 1
                trading_day_list = get_trading_day_range(max_day, lastTradingDay)[1:]
                for month in range(len(trading_day_list))[::betweenDay]:
                    datelist = trading_day_list[month:month + betweenDay]
                    # temp = da.pro.daily(start_date=datelist[0], end_day=datelist[-1])
                    temp = da.pro.query(field, trade_date=datelist[0])
                    data = data.append(temp, ignore_index=True)
                    logging.info('stock_%s:%s') % (field, datelist[0])
                data = data.drop_duplicates(['ts_code', 'trade_date'])
                if not data.empty:
                    data.to_csv(data_file_path)
        data = data.drop_duplicates(['ts_code', 'trade_date'])
        res = data.loc[(data['trade_date'] >= start_date) & (data['trade_date'] <= end_date)]
        res.rename(columns={'ts_code': 'code'}, inplace=True)
        if code is None:
            return res
        else:
            return res.loc[res['code'].isin(code)]

    def sw_weight(self, code=None):
        res = pd.DataFrame()
        #   获取申万一级行业成份股
        for index_code, index_name in INDUSTRY_SW.items():
            temp = swindex.get_index_cons(index_code)[0]
            temp.rename(columns={'index_code': 'code', 'index_name': 'name'}, inplace=True)
            temp['index_code'] = index_code + '.SI'
            temp['index_name'] = index_name
            res = res.append(temp, ignore_index=True)
        res['code'] = [i + '.SH' if i[0] == '6' else i + '.SZ' for i in res['code']]
        if code is None:
            return res
        else:
            return res.loc[res['code'].isin(code)]

da = DataApi()
if __name__ == '__main__':
    da = DataApi()
    weight = da.index_weight(['000300.SH'])
    # sw_weight = da.sw_weight(weight['code'].unique())
    stock_quote = da.stock_bar(weight['code'].unique())
    weight
    # da.pro.daily(weight['code'])
    # da.trading_day()

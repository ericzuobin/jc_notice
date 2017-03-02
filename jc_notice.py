#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2017/3/2 下午6:00
# @Author  : Sahinn
# @File    : jc_notice.py

import re
import urllib
import urllib2
import hashlib
import json

import pymongo
from pymongo import MongoClient

mail_url = 'http://172.16.3.145:82/LeheQ'
client = MongoClient('172.16.3.251', 27017)
mail_reciever = 'sahinn@163.com'
db = client.cp_news
collection = db['jc_notice']


def url_get(url, timeout=30, encoding="utf8"):
    i_headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
                 "Referer": 'http://www.baidu.com'}
    req = urllib2.Request(url, headers=i_headers)
    result = urllib2.urlopen(req, timeout=timeout)
    content = result.read()
    if encoding != "utf8":
        content = unicode(content, encoding).encode("utf8")
    return content


def jc_notice_parser():
    try:
        url = 'http://info.sporttery.cn/iframe/lottery_notice.php'
        div_reg = u'<div.*?sales_tit.*?>(.*?)&nbsp;(.*?)<\/div>\s*<div.*?sales_con.>(.*?)<\/div>'
        content = url_get(url, encoding='gb2312')
        div_group = re.findall(div_reg, content, re.S | re.M)
        pre_map = {}
        for li_line in div_group:
            pre_save(pre_map,  unicode(li_line[0], 'utf-8'), unicode(li_line[1], 'utf-8'), unicode(li_line[2], 'utf-8'))
        filter_news(pre_map)
        news_save(pre_map)
    except Exception, e:
        print e.message


def pre_save(pre_map, title, date, content):
    md5 = hashlib.md5()
    key = title + date + content
    md5.update(key.encode('utf-8'))
    md5_digest = md5.hexdigest()
    pre_map[md5_digest] = {'key': md5_digest, 'title': title, 'date': date, 'is_warning': False, 'content': content}


def filter_news(pre_map):
    if not pre_map:
        return
    keys = []
    for key in pre_map:
        keys.append(key)
    db_news = collection.find({"key": {"$in": keys}}, projection={'key': True, '_id': False})
    for doc in db_news:
        if doc['key'] in pre_map:
            del pre_map[doc['key']]


def news_save(news_map):
    if not news_map:
        return
    docu = []
    for key in news_map:
        docu.append(news_map[key])
    collection.insert_many(docu)


def send_mail():
    db_news = collection.find({"is_warning": False}, projection={'_id': False}).sort('date', pymongo.DESCENDING)
    content = u''
    update_key = []

    if not db_news:
        return
    for doc in db_news:
        update_key.append(doc['key'])
        content += (u"<li><a>%s &nbsp;%s</a>&nbsp;&nbsp;(%s)</li>" % (doc['title'], doc['date'], doc['content']))
    html = u'''<html><head><meta http-equiv=Content-Type content=text/html; charset=utf-8></head><body>
    <h2>竞彩公告更新</h2>
    <ul>''' + content + u'''</ul></body></html>'''
    import datetime
    message = {"content": html, "encoding": "", "fromAddress": "qa@lecai.com", "fromDisplay": "", "htmlStyle": True, "mailType": "",
     "mailto": mail_reciever, "subject": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + u"竞彩公告"}
    request = urllib2.Request(mail_url)
    message = json.dumps(message)
    data = {"q": "mailqueue", "p": "10001", "data": message, "datatype": 'json', "callback": ""}
    try:
        urllib2.urlopen(request, urllib.urlencode(data))
    except:
        return
    if update_key:
        collection.update_many({"key": {"$in": update_key}}, {"$set": {"is_warning": True}})


def main():
    jc_notice_parser()
    send_mail()

if __name__ == "__main__":
    main()

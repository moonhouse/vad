from zipfile import ZipFile
import re
from pathlib import Path
import glob
import datetime
import json
from elasticsearch import Elasticsearch
import os

es = Elasticsearch(os.environ['ELASTIC_URL'],  verify_certs=False)

with open('json_data.json') as json_file:
    mapping = json.load(json_file)

def convert_date(date_string, cut_off, style):
    if style=='old':
        m = re.match(r"(?P<day>\d{1,2})[\/\s]\s{0,2}(?P<month>\d{1,2})[\/\s]\s{0,2}(?P<year>\d{1,2})", date_string)
    else:
        m = re.match(r"(?P<year>\d{2})(?P<month>\d{2})(?P<day>\d{2})", date_string) 
    if m:
        vals = m.groupdict()
        day = int(vals['day'])
        month = int(vals['month'])
        year = int(vals['year'])
        if year < cut_off:
            year = year + 1900
        else:
            year = year + 1800
        try:
            date = datetime.datetime(year, month, day)
            return date
        except ValueError:
            return None
    else:
        return None

page_id = 1

files = glob.glob('zips/*-txt.zip')
for file in files:
    with ZipFile(file) as myzip:
        settings = mapping[Path(file).name]
        pages = filter(lambda file: 'Pages/' in file, myzip.namelist())
        page_nos = [int(Path(x).stem) for x in pages if Path(x).stem.isdigit()]
        for page_no in page_nos:
            page = f"Pages/{page_no:04d}.txt"
            print(f"{file}: {page}")
            with myzip.open(page, mode='r') as mypage:
                page_text = mypage.read().decode('utf-8')
                result = re.finditer(r"(\d{1,2}\/?\s{0,2}\d{1,2}\/?\s{0,2}\d{1,2})", page_text)
                print(f"======={file}==={page}=========")
                dates = [convert_date(res.group(1), settings['published']-1910, settings['datestyle']) for res in result]
                print(dates)
                doc = {
                    'file': file,
                    'page': page_no,
                    'year': settings['published'],
                    'url': f"{settings['url']}{page_no:04d}.html",
                    'qid': settings['qid'],
                    'physical_page': page_no - settings['page_offset'],
                    'contents': page_text,
                    'dates': dates,
                    'updated_at': datetime.datetime.now()
                }
                resp = es.index(index="vad", id=page_id, document=doc)
                print(resp['result'])
                page_id+=1

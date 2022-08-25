from zipfile import ZipFile
import re
from pathlib import Path
import glob
import datetime
import duckdb


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

con = duckdb.connect(database='vem.db', read_only=False)

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
                for res in result:
                    try:
                        day = convert_date(res.group(1), settings['published']-1910, settings['datestyle'])
                        if day:
                            print(res.group(1))
                            print(res.start())
                            print(day)
                            print()
                        # CREATE TABLE date_page(day DATE, file VARCHAR, page SMALLINT, byte_start SMALLINT)
                        # CREATE TABLE candidates(start_page INTEGER, end_page INTEGER, byte_start INTEGER, byte_end INTEGER, born_place VARCHAR, born_date VARCHAR, start_text VARCHAR);;
                            con.execute("INSERT INTO date_page VALUES (?, ?, ?, ?)", [day, Path(file).name, page_no, res.start()])
                    except ValueError:
                        print(page_text)
                        print(res)
                        raise

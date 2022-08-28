import json
from os.path import exists, join
from urllib.request import urlopen
import time


download_folder = 'zips'

with open('json_data.json') as json_file:
    mapping = json.load(json_file)
    for book in mapping:
        if exists(join(download_folder, book)):
            print(f"{book} already downloaded.")
        else:
            print(f"{book} missing, downloading.")
            data = mapping[book]
            work = data['url'].replace('http://runeberg.org/','').strip('/')
            with urlopen( f"http://runeberg.org/download.pl?mode=txtzip&work={work}" ) as webpage:
                content = webpage.read()

            with open( join(download_folder,book), 'wb' ) as download:
                download.write( content )
            time.sleep(10)
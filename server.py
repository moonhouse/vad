import datetime
import os
import urllib.parse
from itertools import chain

import requests
from elasticsearch import Elasticsearch
from flask import Flask, render_template
from markupsafe import Markup

es = Elasticsearch(os.environ['ELASTIC_URL'],  verify_certs=False)
app = Flask(__name__)


def create_quickstatement(hit, qid="LAST"):
    return f"""{qid}|P1343|{hit['qid']}|P958|""|P304|"{hit['physical_page']}"|S854|"{hit['url']}"|S813|+2022-06-04T00:00:00Z/11"""


def name_hits(row, names, dates):
    name_hits = 0
    date_hits = 0
    for name in names:
        if name.lower() in row.lower():
            name_hits += 1
    for date in dates:
        if date in row:
            date_hits += 1
    return f"namehits{name_hits} datehits{date_hits}"


def create_hits(hits, qid="LAST", names=[], dates=[]):
    for hit in hits:
        hit['id'] = hit['_id']
        hit['quickstatement'] = create_quickstatement(hit['_source'], qid)
        for key in hit['_source']:
            hit[key] = hit['_source'][key]
        chunks = hit['_source']['contents'].split('\n')

        new = "\n".join(
            [f"<span class=\"row {name_hits(chunk, names, dates)}\" id=\"row{hit['id']}-{ind}\" data-row=\"{ind}\">{chunk}</span><br/>" for ind, chunk in enumerate(chunks)])

        hit['contents'] = Markup(new)
        hit['person_qid'] = qid
    return hits


def query_wikidata(sparql):
    genders = {'http://www.wikidata.org/entity/Q6581072': 'female',
               'http://www.wikidata.org/entity/Q6581097': 'male', 
               'http://www.wikidata.org/wiki/Q1052281': 'transgender female',
               '': ''}
    faulty_references = requests.get(
        f"https://query.wikidata.org/bigdata/namespace/wdq/sparql?format=json&query={urllib.parse.quote(sparql)}").json()

    results = [{'born': datetime.datetime.strptime(result['fodd']['value'], '%Y-%m-%dT00:00:00Z').strftime('%Y-%m-%d'), 'qid': result['item']['value'].replace(
        'http://www.wikidata.org/entity/', ''), 'label': result['itemLabel']['value'], 'gender': genders[result['gender']['value']] if 'gender' in result else "unknown"} for result in faulty_references['results']['bindings']]
    for result in results:
        result['url'] = f"http://127.0.0.1:5000/date/{result['born']}/{urllib.parse.quote(result['label'])}/{result['qid']}"
    return results


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/list")
def list():
    resp = es.search(index="vad", query={"match_all": {}})
    print("Got %d Hits:" % resp['hits']['total']['value'])
    pages = ""
    for hit in resp['hits']['hits']:
        pages += "<li>%(file)s %(page)s: <a href=\"%(url)s\">%(url)s</a></li>" % hit["_source"]
    return f"<ul>{pages}</ul>"


@app.route("/date/<date>/<string>")
def datelist_string(date, string):
    names = string.split(' ')
    dates = []
    pdate = datetime.datetime.strptime(date, '%Y-%m-%d')
    dates.append(pdate.strftime('%y%m%d'))
    dates.append(pdate.strftime('%-d/%-m/%y'))
    resp = es.search(index="vad", size=30, query={"bool": {"must": {"term": {"dates": date}}, "should": [
                     {"match": {"contents": string}}], "minimum_should_match": 1, "boost": 1.0}}, sort="year")
    print("Got %d Hits:" % resp['hits']['total']['value'])
    hits = create_hits(resp['hits']['hits'], "LAST", names=names, dates=dates)
    return render_template('dates.html', hits=hits, date=date)


@app.route("/date/<date>/<string>/<qid>")
def datelist_string_qid(date, string, qid):
    names = string.split(' ')
    dates = []
    pdate = datetime.datetime.strptime(date, '%Y-%m-%d')
    dates.append(pdate.strftime('%y%m%d'))
    dates.append(pdate.strftime('%-d/%-m/%y'))
    resp = es.search(index="vad", size=30, query={"bool": {"must": {"term": {"dates": date}}, "should": [
                     {"match": {"contents": string}}], "minimum_should_match": 1, "boost": 1.0}}, sort="year")
    print("Got %d Hits:" % resp['hits']['total']['value'])
    hits = create_hits(resp['hits']['hits'], qid, names=names, dates=dates)
    return render_template('dates.html', hits=hits, date=date)


@app.route("/date/<date>")
def datelist(date):
    dates = []
    pdate = datetime.datetime.strptime(date, '%Y-%m-%d')
    dates.append(pdate.strftime('%y%m%d'))
    dates.append(pdate.strftime('%-d/%-m/%y'))
    resp = es.search(index="vad", size=30, query={"bool": {"must": {"term": {"dates": date}}}}, sort="year")
    print("Got %d Hits:" % resp['hits']['total']['value'])
    hits = create_hits(resp['hits']['hits'], None, dates=dates)
    return render_template('dates.html', hits=hits, date=date)


@app.route("/person/<person>")
def personlist(person):
    resp = es.search(index="vad", query={
                     "bool": {"should": [{"match": {"contents": person}}], "minimum_should_match": 1, "boost": 1.0}})
    print("Got %d Hits:" % resp['hits']['total']['value'])
    hits = create_hits(resp['hits']['hits'])
    return render_template('dates.html', hits=hits, date="")


@app.route("/qid/<qid>")
def find_person(qid):
    resp = es.search(index="vad", query={
                     "bool": {"should": [{"match": {"contents": person}}], "minimum_should_match": 1, "boost": 1.0}})
    print("Got %d Hits:" % resp['hits']['total']['value'])
    hits = create_hits(resp['hits']['hits'])
    return render_template('dates.html', hits=hits, date="")


@app.route("/miss/")
def misses():
    sparql = (
        f'SELECT DISTINCT ?item ?itemLabel ?fornamn ?fornamnLabel ?efternamnLabel ?fodd WHERE {{'
        f'  ?item p:P1343 ?statement0.'
        f'  ?statement0 (ps:P1343/(wdt:P279*)) wd:Q5637701.'
        f'  ?item wdt:P735 ?fornamn;'
        f'    wdt:P734 ?efternamn;'
        f'    wdt:P569 ?fodd.'
        f'  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "sv,en". }}'
        f'}}'
    )
    results = query_wikidata(sparql)
    return render_template('hits.html', hits=results)


@app.route("/nondescribed/<year>")
def nondescribed(year):
    year = int(year)
    sparql = (f'SELECT DISTINCT ?item ?itemLabel ?fodd WHERE '
              f'{{'
              f'?item p:P31 ?statement0.'
              f'?statement0 (ps:P31/(wdt:P279*)) wd:Q5.'
              f'?item p:P27 ?statement1.'
              f'?statement1 (ps:P27/(wdt:P279*)) wd:Q34.'
              f'?item p:P569 ?statement_2.'
              f'?statement_2 psv:P569 ?statementValue_2.'
              f'?statementValue_2 wikibase:timePrecision ?precision_2.'
              f'?item wdt:P569 ?fodd.'
              f'FILTER(?precision_2 >= 11 )'
              f'?statementValue_2 wikibase:timeValue ?P569_2.'
              f'FILTER(?P569_2 > "+{year}-01-01T00:00:00Z"^^xsd:dateTime)'
              f'?item p:P569 ?statement_3.'
              f'?statement_3 psv:P569 ?statementValue_3.'
              f'?statementValue_3 wikibase:timePrecision ?precision_3.'
              f'FILTER(?precision_3 >= 11 )'
              f'?statementValue_3 wikibase:timeValue ?P569_3.'
              f'FILTER(?P569_3 < "+{year+1}-01-01T00:00:00Z"^^xsd:dateTime)'
              f'OPTIONAL{{?item wdt:P21 ?gender.}}'
              f'MINUS'
              f'{{'
              f'?item p:P1343 ?statement4.'
              f'?statement4 (ps:P1343/(wdt:P279*)) _:anyValueP1343.'
              f'}}'
              f'    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "sv,en,[AUTO_LANGUAGE]". }}'
              f'}} '
              f'LIMIT 100')
    results = query_wikidata(sparql)
    return render_template('hits.html', hits=results)


@app.route("/nondescribed-test/<year>")
def nondescribed_test(year):
    year = int(year)
    sparql = (f'SELECT DISTINCT ?item ?itemLabel ?fodd ?gender WHERE '
              f'{{'
              f'?item p:P31 ?statement0.'
              f'?statement0 (ps:P31/(wdt:P279*)) wd:Q5.'
              f'?item p:P27 ?statement1.'
              f'?statement1 (ps:P27/(wdt:P279*)) wd:Q34.'
              f'?item p:P569 ?statement_2.'
              f'?statement_2 psv:P569 ?statementValue_2.'
              f'?statementValue_2 wikibase:timePrecision ?precision_2.'
              f'?item wdt:P569 ?fodd.'
              f'FILTER(?precision_2 >= 11 )'
              f'?statementValue_2 wikibase:timeValue ?P569_2.'
              f'FILTER(?P569_2 > "+{year}-01-01T00:00:00Z"^^xsd:dateTime)'
              f'?item p:P569 ?statement_3.'
              f'?statement_3 psv:P569 ?statementValue_3.'
              f'?statementValue_3 wikibase:timePrecision ?precision_3.'
              f'FILTER(?precision_3 >= 11 )'
              f'?statementValue_3 wikibase:timeValue ?P569_3.'
              f'FILTER(?P569_3 < "+{year+1}-01-01T00:00:00Z"^^xsd:dateTime)'
              f'OPTIONAL{{?item wdt:P21 ?gender.}}'
              f'MINUS'
              f'{{'
              f'?item p:P1343 ?statement4.'
              f'?statement4 (ps:P1343/(wdt:P279*)) _:anyValueP1343.'
              f'}}'
              f'    SERVICE wikibase:label {{ bd:serviceParam wikibase:language "sv,en,[AUTO_LANGUAGE]". }}'
              f'}} '
              f'LIMIT 200')
    wd_items = query_wikidata(sparql)
    searches = [[{"index": "vad"}, {"track_scores": True, "sort": "year", "query": {"bool": {"must": {"term": {
        "dates": x['born']}}, "should": [{"match": {"contents": x['label']}}], "minimum_should_match": 1, "boost": 1.0}}}] for x in wd_items]
    searches = [item for sublist in searches for item in sublist]
    resp = es.msearch(body=searches)
    results = resp.body['responses']
    for idx, item in enumerate(wd_items):
        item['results'] = results[idx]
    wd_items = sorted(wd_items, key=lambda item: item['results']['hits']['max_score'] or 0, reverse=True)
    wd_items = [item for item in wd_items if item['results']['hits']['total']['value'] > 0]
    return render_template('newhits.html', hits=wd_items)


@app.route("/nondescribed-day/<month>/<day>")
def nondescribed_day(month, day):
    month = int(month)
    day = int(day)
    sparql = (f'SELECT DISTINCT ?item ?itemLabel ?fodd ?gender WHERE {{'
              f'  ?item p:P31 ?statement0.'
              f'  ?statement0 (ps:P31/(wdt:P279*)) wd:Q5.'
              f'  ?item p:P27 ?statement1.'
              f'  ?statement1 (ps:P27/(wdt:P279*)) wd:Q34.'
              f'  ?item p:P569 ?statement_2.'
              f'  ?statement_2 psv:P569 ?statementValue_2.'
              f'  ?statementValue_2 wikibase:timePrecision ?precision_2.'
              f'  ?item wdt:P569 ?fodd.'
              f'  FILTER(xsd:integer(MONTH(?fodd)) = {month} && xsd:integer(DAY(?fodd)) = {day})'
              f'  FILTER(?precision_2 >= 11 )'
              f'  ?statementValue_2 wikibase:timeValue ?P569_2.'
              f'  FILTER(?P569_2 > "+1850-01-01T00:00:00Z"^^xsd:dateTime)'
              f'  ?item p:P569 ?statement_3.'
              f'  ?statement_3 psv:P569 ?statementValue_3.'
              f'  ?statementValue_3 wikibase:timePrecision ?precision_3.'
              f'  FILTER(?precision_3 >= 11 )'
              f'  ?statementValue_3 wikibase:timeValue ?P569_3.'
              f'  FILTER(?P569_3 < "+1970-01-01T00:00:00Z"^^xsd:dateTime)'
              f'  OPTIONAL{{?item wdt:P21 ?gender.}}'
              f'  MINUS {{'
              f'    ?item p:P1343 ?statement4.'
              f'    ?statement4 (ps:P1343/(wdt:P279*)) _:anyValueP1343.'
              f'  }}'
              f'  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "sv,en,[AUTO_LANGUAGE]". }}'
              f'}}'
              f'LIMIT 100')

    wd_items = query_wikidata(sparql)
    searches = [[{"index": "vad"}, {"track_scores": True, "sort": "year", "query": {"bool": {"must": {"term": {
        "dates": x['born']}}, "should": [{"match": {"contents": x['label']}}], "minimum_should_match": 1, "boost": 1.0}}}] for x in wd_items]
    searches = [item for sublist in searches for item in sublist]
    resp = es.msearch(body=searches)
    results = resp.body['responses']
    for idx, item in enumerate(wd_items):
        item['results'] = results[idx]
    wd_items = sorted(wd_items, key=lambda item: item['results']['hits']['max_score'] or 0, reverse=True)
    wd_items = [item for item in wd_items if item['results']['hits']['total']['value'] > 0]
    return render_template('newhits.html', hits=wd_items)


@app.route("/no-reference/<qid>")
def no_reference_described(qid):
    sparql = (
        f'        SELECT DISTINCT ?item ?itemLabel ?fodd ?gender WHERE {{'
        f'      ?item p:P31 ?statement0.'
        f'      ?statement0 (ps:P31/(wdt:P279*)) wd:Q5.'
        f'      ?item p:P27 ?statement1.'
        f'      ?statement1 (ps:P27/(wdt:P279*)) wd:Q34.'
        f'  ?item wdt:P569 ?fodd.'
        f'  OPTIONAL{{?item wdt:P21 ?gender.}}'
        f'        ?item p:P1343 ?statement2.'
        f'        ?statement2 (ps:P1343/(wdt:P279*)) wd:{qid}.'
        f'        FILTER(NOT EXISTS {{ ?statement2 prov:wasDerivedFrom ?reference. }})'
        f'  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "sv,en,[AUTO_LANGUAGE]". }}'
        f'    }}'
        f'    LIMIT 100'
    )
    wd_items = query_wikidata(sparql)
    searches = [[{"index": "vad"}, {"track_scores": True, "sort": "year", "query": {"bool": {"must": {"term": {
        "dates": x['born']}}, "should": [{"match": {"contents": x['label']}}], "minimum_should_match": 1, "boost": 1.0}}}] for x in wd_items]
    searches = [item for sublist in searches for item in sublist]
    resp = es.msearch(body=searches)
    results = resp.body['responses']
    for idx, item in enumerate(wd_items):
        item['results'] = results[idx]
    wd_items = sorted(wd_items, key=lambda item: item['results']['hits']['max_score'] or 0, reverse=True)
    wd_items = [item for item in wd_items if item['results']['hits']['total']['value'] > 0]
    return render_template('newhits.html', hits=wd_items)

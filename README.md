# vad
Web UI for finding matching bios based on dates

## .env file
Elasticsearch endpoint with username and password needs to be configured in .env. See .env-template for example.

## Setup Elastic

From instructions at https://hub.docker.com/_/elasticsearch

````bash
docker network create vadnetwork
docker run -d --name vadelasticsearch --net vadnetwork -p 9200:9200 -p 9300:9300 -e ELASTIC_PASSWORD=gurkmeja -e "discovery.type=single-node" 
elasticsearch:8.2.2
````

## Index pages
````bash
pipenv run python index.py
````

## Start server

````bash
FLASK_ENV=development FLASK_APP=server pipenv run flask run
````

# Setup DuckDB database

A database is not needed for indexing in Elasticsearch. But might be useful for other uses. 

````bash
duckdb vem.db
````

````SQL
CREATE TABLE date_page("day" DATE, file VARCHAR, page SMALLINT, byte_start SMALLINT);
````

## Example

|    day     |          file          | page | byte_start |
|------------|------------------------|------|------------|
| 1898-02-03 | vemochvad-1967-txt.zip | 7    | 101        |
| 1904-11-22 | vemochvad-1967-txt.zip | 8    | 227        |
| 1889-12-08 | vemochvad-1967-txt.zip | 8    | 1612       |
| 1919-09-20 | vemochvad-1967-txt.zip | 8    | 2287       |
| 1906-11-26 | vemochvad-1967-txt.zip | 8    | 3080       |
| 1897-07-09 | vemochvad-1967-txt.zip | 9    | 535        |
| 1899-04-07 | vemochvad-1967-txt.zip | 9    | 1221       |
| 1932-04-10 | vemochvad-1967-txt.zip | 9    | 2597       |
| 1919-12-28 | vemochvad-1967-txt.zip | 10   | 130        |
| 1890-11-04 | vemochvad-1967-txt.zip | 10   | 907        |

# Extract dates

````bash
pipenv run python list_archives.py
````

# Sparql queries

The /sparql folder contains queries to find candidates for persons to link.

# Acknowledgments
Puzzle favicons are modified versions of [UXWing's Extension icon](https://uxwing.com/extension-icon/). 

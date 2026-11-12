"""Configura la fuente sintetica y las tablas auxiliares oficiales de WebAPI."""
import json
import os
import time
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import URLError
import psycopg
from psycopg import sql

BASE = 'http://webapi:8080/WebAPI'
OUT = Path('/output')
OUT.mkdir(exist_ok=True)


def get(path):
    with urlopen(BASE + path, timeout=120) as response:
        text = response.read().decode()
        return json.loads(text) if response.headers.get_content_type() == 'application/json' else text


deadline = time.monotonic() + 600
while True:
    try:
        get('/source/sources')
        break
    except (URLError, TimeoutError):
        if time.monotonic() > deadline:
            raise RuntimeError('WebAPI no estuvo disponible en 600 segundos') from None
        time.sleep(5)

with psycopg.connect(host='omop-db', dbname='omop', user='omop', password=os.environ['OMOP_DB_PASSWORD']) as db:
    with db.cursor() as cur:
        cur.execute("SELECT to_regclass('cdm.person'), to_regclass('achilles_results.achilles_results')")
        if not all(cur.fetchone()):
            raise RuntimeError('Ejecutar primero quality-prepare y quality achilles.')
        cur.execute('CREATE SCHEMA IF NOT EXISTS atlas_results')
        cur.execute('CREATE SCHEMA IF NOT EXISTS scratch')
        cur.execute("SELECT to_regclass('atlas_results.cohort')")
        if cur.fetchone()[0] is None:
            ddl = get('/ddl/results?' + urlencode(dict(dialect='postgresql', schema='atlas_results', vocabSchema='cdm', tempSchema='scratch', initConceptHierarchy='true')))
            if not isinstance(ddl, str):
                raise RuntimeError('WebAPI no devolvio DDL SQL como texto')
            (OUT / 'results-ddl.sql').write_text(ddl)
            cur.execute(ddl)
        # Copia de resultados para que Achilles pueda recrear sus tablas en futuras cargas.
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='achilles_results' AND table_name LIKE 'achilles_%'")
        for (table,) in cur.fetchall():
            cur.execute("SELECT table_type FROM information_schema.tables WHERE table_schema='atlas_results' AND table_name=%s", (table,))
            existing = cur.fetchone()
            if existing and existing[0] == 'VIEW':
                cur.execute(sql.SQL('DROP VIEW atlas_results.{}').format(sql.Identifier(table)))
            cur.execute(sql.SQL('CREATE TABLE IF NOT EXISTS atlas_results.{} (LIKE achilles_results.{} INCLUDING ALL)').format(sql.Identifier(table), sql.Identifier(table)))
            cur.execute(sql.SQL('DELETE FROM atlas_results.{}').format(sql.Identifier(table)))
            cur.execute(sql.SQL('INSERT INTO atlas_results.{} SELECT * FROM achilles_results.{}').format(sql.Identifier(table), sql.Identifier(table)))
        ddl = get('/ddl/achilles?' + urlencode(dict(dialect='postgresql', schema='atlas_results', vocabSchema='cdm')))
        (OUT / 'concept-count-ddl.sql').write_text(ddl)
        cur.execute(ddl)

jdbc = 'jdbc:postgresql://omop-db:5432/omop?' + urlencode({'user': 'omop', 'password': os.environ['OMOP_DB_PASSWORD']})
with psycopg.connect(host='webapi-db', dbname='webapi', user='webapi', password=os.environ['WEBAPI_DB_PASSWORD']) as db:
    with db.cursor() as cur:
        cur.execute("SELECT source_id FROM webapi.source WHERE source_key='FHIR_DEMO'")
        old = cur.fetchone()
        if old:
            source_id = old[0]
            cur.execute("UPDATE webapi.source SET source_connection=%s, source_name='FHIR synthetic laboratory', source_dialect='postgresql' WHERE source_id=%s", (jdbc, source_id))
        else:
            cur.execute("INSERT INTO webapi.source(source_id,source_name,source_key,source_connection,source_dialect) VALUES(nextval('webapi.source_sequence'),'FHIR synthetic laboratory','FHIR_DEMO',%s,'postgresql') RETURNING source_id", (jdbc,))
            source_id = cur.fetchone()[0]
        for kind, schema, priority in [(0, 'cdm', 0), (1, 'cdm', 1), (2, 'atlas_results', 1), (5, 'scratch', 0)]:
            cur.execute('SELECT source_daimon_id FROM webapi.source_daimon WHERE source_id=%s AND daimon_type=%s', (source_id, kind))
            old = cur.fetchone()
            if old:
                cur.execute('UPDATE webapi.source_daimon SET table_qualifier=%s,priority=%s WHERE source_daimon_id=%s', (schema, priority, old[0]))
            else:
                cur.execute("INSERT INTO webapi.source_daimon(source_daimon_id,source_id,daimon_type,table_qualifier,priority) VALUES(nextval('webapi.source_daimon_sequence'),%s,%s,%s,%s)", (source_id, kind, schema, priority))

get('/source/refresh')
sources = get('/source/sources')
if not any(source.get('sourceKey') == 'FHIR_DEMO' for source in sources):
    raise RuntimeError('WebAPI no publico la fuente configurada')
print(json.dumps({'source': 'FHIR_DEMO', 'cdm': 'cdm', 'results': 'atlas_results', 'vocabulary': 'NOT LOADED'}))

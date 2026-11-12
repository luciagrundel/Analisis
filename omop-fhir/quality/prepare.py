"""Copia reproducible del prototipo en un esquema CDM completo para evaluacion."""
import json
from pathlib import Path
import psycopg
from psycopg import sql

with psycopg.connect('') as db:
    with db.cursor() as cur:
        cur.execute('SELECT pg_advisory_xact_lock(540019)')
        cur.execute('CREATE SCHEMA IF NOT EXISTS cdm')
        cur.execute('CREATE SCHEMA IF NOT EXISTS achilles_results')
        cur.execute('CREATE SCHEMA IF NOT EXISTS dqd_results')
        cur.execute('CREATE SCHEMA IF NOT EXISTS scratch')
        cur.execute("SELECT to_regclass('cdm.person')")
        if cur.fetchone()[0] is None:
            ddl = Path('/quality/OMOPCDM_postgresql_5.4_ddl.sql').read_text()
            cur.execute(ddl.replace('@cdmDatabaseSchema', 'cdm'))
        # Solo refresca las tablas alimentadas por esta copia; no cambia public.
        for table in ('person', 'visit_occurrence', 'condition_occurrence', 'measurement'):
            cur.execute(sql.SQL('DELETE FROM cdm.{}').format(sql.Identifier(table)))
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position", (table,))
            columns = [r[0] for r in cur.fetchall()]
            names = sql.SQL(',').join(map(sql.Identifier, columns))
            values = sql.SQL(',').join(
                sql.SQL('{}::date').format(sql.Identifier(c)) if c.endswith('_date') else sql.Identifier(c)
                for c in columns)
            cur.execute(sql.SQL('INSERT INTO cdm.{} ({}) SELECT {} FROM public.{}').format(sql.Identifier(table), names, values, sql.Identifier(table)))
        cur.execute('DELETE FROM cdm.observation_period')
        cur.execute('''INSERT INTO cdm.observation_period
            SELECT row_number() OVER (ORDER BY person_id), person_id, MIN(event_date), MAX(event_date), 0
            FROM (SELECT person_id, visit_start_date::date AS event_date FROM public.visit_occurrence
              UNION ALL SELECT person_id, visit_end_date::date FROM public.visit_occurrence
              UNION ALL SELECT person_id, condition_start_date::date FROM public.condition_occurrence
              UNION ALL SELECT person_id, measurement_date::date FROM public.measurement) events
            GROUP BY person_id''')
        # Sentinel OMOP: no representa un vocabulario Athena cargado.
        cur.execute('DELETE FROM cdm.concept WHERE concept_id=0')
        cur.execute("""INSERT INTO cdm.concept VALUES
            (0,'No matching concept','Metadata','None','Undefined',NULL,'0','1970-01-01','2099-12-31',NULL)""")
        cur.execute('DELETE FROM cdm.cdm_source')
        cur.execute("""INSERT INTO cdm.cdm_source VALUES
            ('FHIR synthetic laboratory','FHIR-DEMO','Local laboratory',
             'Synthetic data; vocabulary absent; observation periods inferred from event bounds',
             NULL,NULL,CURRENT_DATE,CURRENT_DATE,'5.4',0,'NOT LOADED')""")
        cur.execute('SELECT COUNT(*) FROM cdm.person')
        count = cur.fetchone()[0]
        if not count:
            raise RuntimeError('No hay pacientes. Ejecutar primero etl demo.')
    print(json.dumps({'schema': 'cdm', 'persons': count, 'vocabulary': 'NOT LOADED',
                      'observation_period': 'inferred event bounds, not enrollment coverage'}))

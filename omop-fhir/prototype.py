"""Laboratorio FHIR R4 -> subconjunto OMOP 5.4. Solo datos sinteticos."""
import argparse
import calendar
import json
import sqlite3
from datetime import date
from pathlib import Path


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS person (
 person_id INTEGER PRIMARY KEY, person_source_value TEXT UNIQUE NOT NULL,
 gender_concept_id INTEGER NOT NULL, year_of_birth INTEGER NOT NULL,
 month_of_birth INTEGER, day_of_birth INTEGER,
 race_concept_id INTEGER NOT NULL DEFAULT 0, ethnicity_concept_id INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS visit_occurrence (
 visit_occurrence_id INTEGER PRIMARY KEY, person_id INTEGER NOT NULL REFERENCES person,
 visit_concept_id INTEGER NOT NULL DEFAULT 0, visit_start_date TEXT NOT NULL,
 visit_end_date TEXT NOT NULL, visit_type_concept_id INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS condition_occurrence (
 condition_occurrence_id INTEGER PRIMARY KEY, person_id INTEGER NOT NULL REFERENCES person,
 condition_concept_id INTEGER NOT NULL DEFAULT 0, condition_start_date TEXT NOT NULL,
 condition_type_concept_id INTEGER NOT NULL DEFAULT 0, condition_source_value TEXT,
 condition_source_concept_id INTEGER NOT NULL DEFAULT 0,
 visit_occurrence_id INTEGER REFERENCES visit_occurrence);
CREATE TABLE IF NOT EXISTS measurement (
 measurement_id INTEGER PRIMARY KEY, person_id INTEGER NOT NULL REFERENCES person,
 measurement_concept_id INTEGER NOT NULL DEFAULT 0, measurement_date TEXT NOT NULL,
 measurement_type_concept_id INTEGER NOT NULL DEFAULT 0, value_as_number REAL NOT NULL,
 unit_concept_id INTEGER NOT NULL DEFAULT 0, measurement_source_value TEXT,
 measurement_source_concept_id INTEGER NOT NULL DEFAULT 0, unit_source_value TEXT,
 visit_occurrence_id INTEGER REFERENCES visit_occurrence);
CREATE TABLE IF NOT EXISTS provenance (
 source TEXT NOT NULL, resource_key TEXT NOT NULL, target_table TEXT NOT NULL,
 target_id INTEGER NOT NULL, version TEXT, resource_json TEXT NOT NULL,
 PRIMARY KEY(source,resource_key));
"""
TABLES = {'Patient': 'person', 'Encounter': 'visit_occurrence',
          'Condition': 'condition_occurrence', 'Observation': 'measurement'}
KEYS = {t: t + '_id' for t in TABLES.values()}


def connect(path):
    if path.startswith(('postgresql://', 'postgres://')):
        from pg_backend import Database
        return Database(path, SCHEMA)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def sample():
    resources = []
    for i in range(1, 11):
        patient, visit = f'Patient/p{i}', f'Encounter/e{i}'
        resources.extend([
            dict(resourceType='Patient', id=f'p{i}', gender='unknown', birthDate=f'{1970+i}-01-01'),
            dict(resourceType='Encounter', id=f'e{i}', status='finished',
                 **{'class': {'system': 'http://terminology.hl7.org/CodeSystem/v3-ActCode', 'code': 'AMB'}},
                 subject={'reference': patient}, period={'start': '2026-11-09', 'end': '2026-11-09'}),
            dict(resourceType='Observation', id=f'g{i}', status='final',
                 code={'coding': [{'system': 'http://loinc.org', 'code': '2345-7'}]},
                 subject={'reference': patient}, encounter={'reference': visit},
                 effectiveDateTime='2026-11-09T09:00:00-03:00',
                 valueQuantity={'value': 80 + i * 10, 'system': 'http://unitsofmeasure.org', 'code': 'mg/dL', 'unit': 'mg/dL'})])
        if i <= 6:
            resources.append(dict(resourceType='Condition', id=f'd{i}',
                subject={'reference': patient}, encounter={'reference': visit},
                clinicalStatus={'coding': [{'system': 'http://terminology.hl7.org/CodeSystem/condition-clinical', 'code': 'active'}]},
                code={'coding': [{'system': 'http://hl7.org/fhir/sid/icd-10-cm', 'code': 'E11.9'}]},
                onsetDateTime='2026-10-01'))
    return {'resourceType': 'Bundle', 'type': 'collection', 'entry': [{'resource': r} for r in resources]}


def day(value):
    return date.fromisoformat(value[:10]).isoformat()


def load(db, bundle, source='synthetic-demo'):
    if bundle.get('resourceType') != 'Bundle' or bundle.get('type') != 'collection':
        raise ValueError('Se requiere un Bundle collection autocontenido.')
    resources = [e['resource'] for e in bundle.get('entry', [])]
    seen = set()
    for r in resources:
        key = r['resourceType'] + '/' + r['id']
        if key in seen:
            raise ValueError('Recurso duplicado: ' + key)
        seen.add(key)
        if r['resourceType'] not in TABLES:
            raise ValueError('Tipo no soportado: ' + r['resourceType'])

    def resolve(ref, expected):
        if not ref.startswith(expected + '/') or len(ref.split('/')) != 2:
            raise ValueError('Solo referencias relativas Tipo/id: ' + ref)
        row = db.execute('SELECT target_id FROM provenance WHERE source=? AND resource_key=?', (source, ref)).fetchone()
        if not row:
            raise ValueError('Referencia no resuelta: ' + ref)
        return row[0]

    with db:
        for kind in TABLES:
            for r in (r for r in resources if r['resourceType'] == kind):
                key, table = kind + '/' + r['id'], TABLES[kind]
                fields = {}
                if kind == 'Patient':
                    birth = date.fromisoformat(r['birthDate'])
                    fields = dict(person_source_value=source + '/' + r['id'], gender_concept_id=0,
                                  year_of_birth=birth.year, month_of_birth=birth.month, day_of_birth=birth.day)
                else:
                    fields['person_id'] = resolve(r['subject']['reference'], 'Patient')
                    if kind == 'Encounter':
                        start, end = day(r['period']['start']), day(r['period']['end'])
                        if end < start:
                            raise ValueError('Encuentro con fechas invertidas: ' + key)
                        fields.update(visit_start_date=start, visit_end_date=end)
                    else:
                        visit = r.get('encounter', {}).get('reference')
                        fields['visit_occurrence_id'] = resolve(visit, 'Encounter') if visit else None
                        if visit:
                            owner = db.execute('SELECT person_id FROM visit_occurrence WHERE visit_occurrence_id=?', (fields['visit_occurrence_id'],)).fetchone()[0]
                            if owner != fields['person_id']:
                                raise ValueError('Encuentro de otro paciente: ' + key)
                        system = 'http://loinc.org' if kind == 'Observation' else 'http://hl7.org/fhir/sid/icd-10-cm'
                        codes = [c['code'] for c in r['code']['coding'] if c.get('system') == system]
                        expected = '2345-7' if kind == 'Observation' else 'E11.9'
                        if expected not in codes:
                            raise ValueError('Codigo fuera del alcance del laboratorio: ' + key)
                        if kind == 'Condition':
                            fields.update(condition_start_date=day(r['onsetDateTime']), condition_source_value=expected)
                        else:
                            q = r['valueQuantity']
                            if r['status'] not in ('final', 'amended', 'corrected'):
                                raise ValueError('Medicion no final: ' + key)
                            if q.get('system') != 'http://unitsofmeasure.org' or q.get('code') != 'mg/dL':
                                raise ValueError('Solo se admite UCUM mg/dL: ' + key)
                            value = q['value']
                            if isinstance(value, bool) or not isinstance(value, (float, int)) or not (-1e308 < value < 1e308):
                                raise ValueError('Valor numerico invalido: ' + key)
                            fields.update(measurement_date=day(r['effectiveDateTime']), value_as_number=value,
                                          measurement_source_value=expected, unit_source_value='mg/dL')
                old = db.execute('SELECT target_id FROM provenance WHERE source=? AND resource_key=?', (source, key)).fetchone()
                if old:
                    target = old[0]
                    db.execute(f'UPDATE {table} SET ' + ','.join(f'{c}=?' for c in fields) + f' WHERE {KEYS[table]}=?', (*fields.values(), target))
                else:
                    target = db.execute(f'INSERT INTO {table} (' + ','.join(fields) + ') VALUES (' + ','.join('?' for _ in fields) + f') RETURNING {KEYS[table]}', tuple(fields.values())).fetchone()[0]
                db.execute('''INSERT INTO provenance VALUES (?,?,?,?,?,?)
                           ON CONFLICT(source,resource_key) DO UPDATE SET
                           target_table=excluded.target_table,target_id=excluded.target_id,
                           version=excluded.version,resource_json=excluded.resource_json''',
                           (source, key, table, target, r.get('meta', {}).get('versionId'), json.dumps(r)))
    return {t: db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in TABLES.values()}


def cohort(db, as_of, threshold):
    end = date.fromisoformat(as_of)
    month_index = end.year * 12 + end.month - 1 - 6
    year, month0 = divmod(month_index, 12)
    start = date(year, month0 + 1, min(end.day, calendar.monthrange(year, month0 + 1)[1]))
    return [dict(r) for r in db.execute('''SELECT p.person_id, p.person_source_value,
        MAX(m.value_as_number) AS max_glucose_mg_dl FROM person p
        JOIN measurement m ON m.person_id=p.person_id
        WHERE m.measurement_source_value='2345-7' AND m.unit_source_value='mg/dL'
        AND m.measurement_date BETWEEN ? AND ? AND m.value_as_number>?
        AND EXISTS (SELECT 1 FROM condition_occurrence c WHERE c.person_id=p.person_id
          AND c.condition_source_value='E11.9' AND c.condition_start_date<=?)
        GROUP BY p.person_id,p.person_source_value ORDER BY p.person_id''',
        (start.isoformat(), end.isoformat(), threshold, end.isoformat()))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['demo', 'load', 'cohort'])
    parser.add_argument('--db', default='demo.db')
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--source', default='synthetic-demo')
    parser.add_argument('--as-of', default='2026-11-09')
    parser.add_argument('--threshold', type=float, default=125)
    args = parser.parse_args()
    with connect(args.db) as db:
        if args.command == 'demo':
            print(json.dumps(load(db, sample(), args.source), indent=2))
        elif args.command == 'load':
            if not args.bundle:
                parser.error('load requiere --bundle')
            print(json.dumps(load(db, json.loads(args.bundle.read_text(encoding='utf-8')), args.source), indent=2))
        if args.command in ('demo', 'cohort'):
            result = cohort(db, args.as_of, args.threshold)
            print(json.dumps({'count': len(result), 'patients': result}, indent=2))


if __name__ == '__main__':
    main()

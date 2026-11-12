"""Comandos Docker: seed, sync, cohort, demo, test, export."""
import argparse
import json
import os
import time
import unittest
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.error import URLError

from prototype import sample, connect, load, cohort, TABLES


def request(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(url, data=data, headers={'Accept': 'application/fhir+json', 'Content-Type': 'application/fhir+json'})
    with urlopen(req, timeout=60) as response:
        return json.load(response)


def wait_ready(base):
    deadline = time.monotonic() + 300
    while True:
        try:
            metadata = request(base + '/metadata')
            if metadata.get('resourceType') != 'CapabilityStatement' or not metadata.get('fhirVersion', '').startswith('4.0.'):
                raise ValueError('Se requiere servidor FHIR R4 4.0.x')
            return
        except (URLError, TimeoutError):
            if time.monotonic() >= deadline:
                raise RuntimeError('HAPI no estuvo disponible dentro de 300 segundos')
            time.sleep(5)


def transaction():
    bundle = sample()
    bundle['type'] = 'transaction'
    for entry in bundle['entry']:
        r = entry['resource']
        key = r['resourceType'] + '/' + r['id']
        entry['request'] = {'method': 'PUT', 'url': key}
    return bundle


def extract(base):
    entries = []
    for kind in TABLES:
        url = base + '/' + kind + '?_count=100'
        visited = set()
        while url:
            if url in visited or urlsplit(url).netloc != urlsplit(base).netloc:
                raise ValueError('Enlace de paginacion inesperado: ' + url)
            visited.add(url)
            page = request(url)
            if page.get('resourceType') != 'Bundle' or page.get('type') != 'searchset':
                raise ValueError('Respuesta de busqueda FHIR invalida')
            entries.extend({'resource': e['resource']} for e in page.get('entry', [])
                           if e.get('search', {}).get('mode') != 'include' and e.get('resource', {}).get('resourceType') == kind)
            next_url = next((link['url'] for link in page.get('link', []) if link['relation'] == 'next'), None)
            url = urljoin(url, next_url) if next_url else None
    return {'resourceType': 'Bundle', 'type': 'collection', 'entry': entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['seed', 'sync', 'cohort', 'demo', 'test', 'export'])
    parser.add_argument('--as-of', default='2026-11-09')
    parser.add_argument('--threshold', type=float, default=125)
    args = parser.parse_args()
    if args.command == 'test':
        suite = unittest.defaultTestLoader.discover('.', pattern='test_*.py')
        raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
    if args.command == 'export':
        Path('examples').mkdir(exist_ok=True)
        for name, bundle in [('collection', sample()), ('transaction', transaction())]:
            Path(f'examples/{name}.json').write_text(json.dumps(bundle, indent=2), encoding='utf-8')
        return
    base = os.environ.get('FHIR_URL', 'http://localhost:8080/fhir').rstrip('/')
    if args.command in ('seed', 'sync', 'demo'):
        wait_ready(base)
    if args.command in ('seed', 'demo'):
        result = request(base, transaction())
        if result.get('type') != 'transaction-response' or any(not e.get('response', {}).get('status', '').startswith('2') for e in result.get('entry', [])) or len(result.get('entry', [])) != 36:
            raise ValueError('Transaccion FHIR incompleta: ' + json.dumps(result))
        print('FHIR: 36 recursos sinteticos cargados por PUT.', flush=True)
    if args.command == 'seed':
        return
    # Los parametros PG* son leidos por libpq, sin construir URLs con contrasenas.
    db = connect('postgresql://')
    if args.command in ('sync', 'demo'):
        print(json.dumps(load(db, extract(base), base), indent=2), flush=True)
    if args.command in ('cohort', 'demo'):
        rows = cohort(db, args.as_of, args.threshold)
        print(json.dumps({'count': len(rows), 'patients': rows}, indent=2))
    db.connection.close()


if __name__ == '__main__':
    main()

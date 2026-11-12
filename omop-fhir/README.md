# Laboratorio FHIR → OMOP

Laboratorio basado en `contexto.md`: HAPI FHIR R4, PostgreSQL y ETL Python. Guarda un **subconjunto educativo** de las tablas PERSON, VISIT_OCCURRENCE, CONDITION_OCCURRENCE y MEASUREMENT de OMOP 5.4. Tambien conserva un modo local SQLite sin dependencias externas.

## Despliegue Docker

Requisitos: Docker Desktop iniciado con contenedores Linux y Docker Compose v2. Reservar al menos 4 GB de RAM para el laboratorio. Ejecutar desde esta carpeta:

```powershell
docker compose up -d --wait
docker compose run --rm etl demo
```

La primera ejecucion descarga las imagenes y construye la ETL. HAPI puede tardar varios minutos en crear su esquema; `demo` espera hasta cinco minutos a que `/metadata` responda como FHIR R4. `up --wait` verifica PostgreSQL; la disponibilidad FHIR se comprueba desde la ETL.

Servicios:

| Servicio | Acceso | Funcion |
| --- | --- | --- |
| HAPI FHIR | http://localhost:8080/fhir/metadata | API FHIR R4 |
| Interfaz HAPI | http://localhost:8080/ | Exploracion del servidor |
| fhir-db | Solo red Docker | PostgreSQL persistente de HAPI |
| omop-db | Solo red Docker | PostgreSQL del subconjunto OMOP |
| etl | Comando temporal | Carga, extraccion paginada, transformacion y cohorte |

El puerto HTTP se publica solo en `127.0.0.1`. Las credenciales por defecto son de laboratorio; se pueden cambiar copiando `.env.example` a `.env` **antes** de crear los volumenes. Cambiar esas variables despues no cambia las contrasenas de una base ya inicializada. HAPI no tiene autenticacion: usar solo datos sinteticos y no publicar este entorno en Internet.

La imagen HAPI esta fijada al digest comprobado en este laboratorio. `HAPI_IMAGE` permite cambiarla deliberadamente. PostgreSQL y Python usan tags de version; para congelar todo el entorno, fijar tambien sus digests. Registrar las imagenes utilizadas con `docker compose images`.

## Ejemplos de extremo a extremo

La demo ejecuta `seed` → `sync` → `cohort`. Tambien se puede hacer por pasos:

```powershell
# 1. Enviar Bundle transaction con PUT: repetir no crea nuevos IDs FHIR.
docker compose run --rm etl seed

# 2. Consultar HAPI, seguir paginas y transformar todo el conjunto soportado.
docker compose run --rm etl sync

# 3. Consultar PostgreSQL: resultado esperado 2 pacientes (p5 y p6).
docker compose run --rm etl cohort --as-of 2026-11-09 --threshold 125

# 4. Pruebas de transformacion, rollback e idempotencia.
docker compose run --rm --no-deps etl test

# 5. Consultar FHIR desde PowerShell.
Invoke-RestMethod 'http://localhost:8080/fhir/Patient/p5'
Invoke-RestMethod 'http://localhost:8080/fhir/Observation?subject=Patient/p5'

# 6. Ejecutar los ejemplos SQL directamente en PostgreSQL.
Get-Content -Raw examples/queries.sql | docker compose exec -T omop-db psql -U omop -d omop
```

Archivos de ejemplo:

- [examples/transaction.json](examples/transaction.json): 36 recursos sinteticos para POST a `/fhir`, con IDs estables.
- [examples/collection.json](examples/collection.json): los mismos datos para el modo local.
- [examples/requests.http](examples/requests.http): consultas y carga desde REST Client de VS Code; tambien se pueden reproducir en Postman.
- [examples/postman_collection.json](examples/postman_collection.json): coleccion para importar directamente en Postman, con consultas al servidor local.
- [examples/queries.sql](examples/queries.sql): conteos, cohorte y trazabilidad.

Resultado esperado en una base nueva: **10 personas, 10 visitas, 6 condiciones, 10 mediciones; cohorte de 2 personas**. Los datos estan fechados en octubre/noviembre de 2026 para que el resultado sea reproducible con `--as-of 2026-11-09`.

Verificado el 09/11/2026: despliegue Docker, carga y recarga completa sin duplicados, consultas SQL y 7 pruebas automatizadas satisfactorias. Los `person_id` dependen del orden de extraccion; identificar los ejemplos por `person_source_value` (p5 y p6).

`sync` recorre todos los recursos de los cuatro tipos en este servidor de laboratorio. No implementa extraccion incremental ni una instantanea consistente ante cambios concurrentes. Si se agregan codigos/unidades/campos fuera del alcance, la carga falla y revierte sus cambios; no se omiten silenciosamente. El servidor debe estar dedicado a estos ejemplos. La identidad de la fuente usa la URL interna `http://hapi:8080/fhir`; cambiarla genera otra fuente.

## Achilles y Data Quality Dashboard

Ya ejecutados sobre los datos sinteticos: [resultado y limitaciones](quality/RESULTADOS.md). El visor DQD esta disponible en http://localhost:8090 mientras su contenedor este iniciado.

Se agregaron servicios de evaluacion OHDSI. Ejecutar sobre los datos sinteticos ya cargados:

```powershell
docker compose run --rm quality-prepare
docker compose run --rm quality all
```

Tambien se pueden ejecutar por separado:

```powershell
docker compose run --rm quality achilles
docker compose run --rm quality dqd
```

`quality-prepare` crea el esquema `cdm` con las tablas oficiales OMOP 5.4 y refresca una copia de las cuatro tablas del prototipo. Convierte las fechas a `date` y genera periodos de observacion con los limites de los eventos disponibles. Estos periodos **no representan afiliacion ni cobertura observacional verificada**. Las tablas originales en `public` permanecen intactas. Volver a ejecutar el preparador despues de cada nueva carga ETL y luego repetir los analisis. Evitar ejecutar varias evaluaciones simultaneamente.

Los resultados se escriben en PostgreSQL:

- `achilles_results.achilles_results` y `achilles_results.achilles_results_dist`.
- `dqd_results.dqdashboard_results`.
- El esquema `scratch` aloja tablas de trabajo.

Y se conservan archivos locales en `output/quality`, incluidos `dqd/results.json`, logs, SQL generado, versiones de paquetes y `sessionInfo.txt`. Esta carpeta esta excluida de Git.

Para visualizar el resultado con el dashboard oficial de DQD:

```powershell
docker compose up -d dqd-dashboard
```

Abrir http://localhost:8090. Despues de repetir los controles, reiniciar el visor con `docker compose restart dqd-dashboard` para que vuelva a leer el JSON. El visor no ejecuta controles; presenta la ultima evaluacion guardada. `output/quality/run-status.json` registra el estado de cada proceso. Las carpetas `previous-errors-*` conservan errores de ejecuciones anteriores para diagnostico.

La copia tiene la estructura completa, pero **todavia no tiene los vocabularios Athena**. Solo incorpora el concepto 0 de ausencia de correspondencia; no inventa mapeos. Los fallos de calidad y los resultados descriptivos limitados son esperables. Una ejecucion exitosa significa que se pudieron calcular controles, no que la base sea apta para investigacion. Achilles usa `smallCellCount=0` exclusivamente porque son diez pacientes sinteticos; no reutilizar esta configuracion con datos reales.

La imagen OHDSI contiene R/Java y es considerablemente mas grande que la ETL. Consultar [fuentes y version del DDL](quality/SOURCES.md). La visualizacion ARES no se instala en esta etapa.

Consultas de los resultados en [examples/quality.sql](examples/quality.sql):

```powershell
Get-Content -Raw examples/quality.sql | docker compose exec -T omop-db psql -U omop -d omop
```

## ATLAS

Se agregaron ATLAS, WebAPI y una base de configuracion persistente. Consultar [inicio, acceso y limitaciones](atlas/README.md).

```powershell
docker compose up -d webapi atlas
docker compose run --rm atlas-init
```

Acceso: http://localhost:8091/atlas/. Fuente: **FHIR synthetic laboratory**. Requiere la copia `cdm` y Achilles ya ejecutado. Los vocabularios Athena siguen pendientes.

## Administrar los contenedores

```powershell
docker compose ps
docker compose logs --tail=100 hapi
docker compose stop
docker compose start
# Elimina contenedores y red, conserva los datos:
docker compose down
```

Los volumenes `fhir-data` y `omop-data` conservan los datos entre reinicios. `docker compose down -v` los elimina definitivamente: usarlo solo para reiniciar deliberadamente el laboratorio. Si el puerto 8080 esta ocupado, cambiar el puerto del lado izquierdo en `compose.yaml`; la ETL interna no requiere cambios.

## Ejecutar

```powershell
py -3 prototype.py demo
py -3 prototype.py cohort --as-of 2026-11-09 --threshold 125
py -3 -m unittest -v
```

La demo crea `demo.db` con 10 pacientes, 10 encuentros, 6 diagnósticos y 10 mediciones sintéticas. La cohorte devuelve **2 pacientes** con código ICD-10-CM E11.9 y glucosa LOINC 2345-7 superior a 125 mg/dL en los seis meses calendario anteriores a la fecha de corte, incluyendo ambos extremos. No constituye una definición clínica validada de diabetes. El diagnóstico debe estar registrado antes o en la fecha de corte.

Para cargar un archivo propio de prueba:

```powershell
py -3 prototype.py load --bundle datos.json --source hospital-demo --db laboratorio.db
py -3 prototype.py cohort --db laboratorio.db --as-of 2026-11-09
```

Usar el mismo `--source` conserva identidad e IDs al recargar; fuentes diferentes permanecen separadas. Se admiten referencias relativas `Patient/id` y `Encounter/id`. El Bundle puede estar desordenado. Las referencias deben existir en el Bundle o en una carga anterior de esa fuente. Una carga inválida revierte sus cambios completos.

## Reglas y trazabilidad

| Recurso | Destino | Alcance |
| --- | --- | --- |
| Patient | person | Fecha de nacimiento completa obligatoria |
| Encounter | visit_occurrence | Inicio y fin obligatorios |
| Condition | condition_occurrence | ICD-10-CM E11.9; onsetDateTime obligatorio |
| Observation | measurement | LOINC 2345-7; valor numérico; UCUM mg/dL; final/amended/corrected |

`provenance` vincula fuente, Tipo/id, versión, JSON original y fila destino. Se conserva la versión más recientemente cargada, sin historial. Las actualizaciones reemplazan los campos derivados manteniendo el ID; no se compara el orden de versiones. No se implementan eliminaciones ni conciliación entre fuentes.

Los concept_id quedan en **0 (sin mapeo)**, incluidos sexo, tipo y unidad. Se conservan códigos fuente para practicar la transformación sin inventar identificadores de vocabulario. La cohorte consulta estos códigos explícitos; no usa jerarquías OMOP. Unidades distintas de mg/dL y códigos fuera del alcance se rechazan. No se realiza validación FHIR completa, interpretación del estado clínico de Condition ni conversión de unidades.

## Siguiente etapa de la arquitectura

1. Reemplazar el subconjunto por el DDL oficial completo OMOP CDM 5.4. Los esquemas actuales SQLite/PostgreSQL **no son una instancia CDM completa ni estan listos para ATLAS/DataQualityDashboard**.
2. Agregar autenticacion, extraccion incremental y control de cambios concurrentes sobre la extraccion paginada ya disponible.
3. Importar vocabularios Athena autorizados, resolver conceptos fuente/estándar, dominios, unidades y procedencia; registrar mapeos y rechazos.
4. Agregar observación temporal, historial, correcciones/eliminaciones, validación FHIR y controles de calidad antes de integrar herramientas OHDSI.

Solo datos sintéticos. No incorpora autenticación, seudonimización ni controles para datos asistenciales reales.

## Referencias

- [OMOP CDM 5.4](https://ohdsi.github.io/CommonDataModel/cdm54.html)
- [FHIR R4 Bundle](https://www.hl7.org/fhir/R4/bundle.html)
- [Athena](https://athena.ohdsi.org/)
- [Configuracion Docker y PostgreSQL de HAPI](https://github.com/hapifhir/hapi-fhir-jpaserver-starter)

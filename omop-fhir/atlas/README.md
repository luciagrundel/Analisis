# ATLAS en el laboratorio

ATLAS: http://localhost:8091/atlas/

WebAPI se publica bajo el mismo origen en http://localhost:8091/WebAPI/ mediante el proxy Nginx de ATLAS. Las bases PostgreSQL permanecen en la red Docker.

`USE_DYNAMIC_WEBAPI_URL=false` conserva el puerto de `WEBAPI_URL`. La configuracion automatica de esta imagen usa `window.location.hostname` y pierde el puerto 8091. Si se cambia el puerto publicado, actualizar tambien `WEBAPI_URL` en Compose. Despues de cambiar la configuracion, recargar ATLAS con Ctrl+F5.

## Iniciar

Requiere la copia `cdm` y los resultados de Achilles de los pasos anteriores:

```powershell
docker compose up -d webapi atlas
docker compose run --rm atlas-init
```

En una instalacion nueva, ejecutar antes `etl demo`, `quality-prepare` y `quality achilles`, como se describe en el README principal.

`atlas-init` espera el arranque de WebAPI, solicita su DDL oficial, crea el esquema auxiliar `atlas_results` y registra la fuente `FHIR_DEMO`. Copia las tablas de resultados de Achilles a ese esquema y reconstruye los conteos auxiliares. Los archivos SQL generados se guardan en `output/atlas`.

La configuracion y las definiciones de ATLAS se guardan en la base `webapi`, volumen `atlas-config-data`. La configuracion de ejemplo es local y sin autenticacion, solo para datos sinteticos. Se recomienda reservar al menos 6 GB para el conjunto completo de servicios. No publicar el puerto en Internet.

## Explorar

1. Abrir ATLAS y entrar en **Data Sources**.
2. Seleccionar **FHIR synthetic laboratory**.
3. Explorar los resultados descriptivos disponibles de Achilles.

La base aun tiene conceptos en 0 y no contiene los vocabularios Athena. Por eso no se esperan busquedas utiles de SNOMED/LOINC ni cohortes clinicas validadas. Los resultados por conceptos pueden estar vacios aunque existan registros fuente. El dashboard DQD permanece en http://localhost:8090.

Validado mediante API: la fuente `FHIR_DEMO` esta registrada; `/WebAPI/cdmresults/FHIR_DEMO/dashboard` devuelve 10 personas y distribucion de edades. ATLAS usa la imagen version 2.15.0 fijada por digest; WebAPI usa el tag oficial 2.15.2 (su endpoint `/info` informa 2.15.1). La revision visual no pudo realizarse porque Chrome estaba minimizado.

## Actualizar los datos

La ETL escribe en `public`; ATLAS consulta la copia `cdm`. Despues de una carga nueva, ejecutar `quality-prepare`, repetir Achilles y ejecutar `atlas-init` para refrescar la configuracion auxiliar segun corresponda. Las cohortes existentes no se regeneran automaticamente.

## Referencias

- https://github.com/OHDSI/WebAPI/wiki/CDM-Configuration
- https://github.com/OHDSI/Broadsea
- https://github.com/OHDSI/Atlas

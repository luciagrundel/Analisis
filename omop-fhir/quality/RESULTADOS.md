# Evaluacion del laboratorio — 2026-11-09

Ejecutado contra la copia de 10 personas sinteticas en `cdm`. Las tablas de origen de la ETL en `public` se conservaron.

## Achilles 1.7.2

- Resultados en `achilles_results`.
- `achilles_results`: 270 filas, correspondientes a 208 analysis_id con resultados.
- El analisis 1 confirma 10 personas.
- No se aplico supresion de celdas pequenas porque todos los datos son sinteticos.

## Data Quality Dashboard 2.8.0

| Resultado | Controles |
| --- | ---: |
| Total | 2374 |
| Errores de ejecucion SQL | 0 |
| Fallidos por umbral | 19 |
| Aprobados aplicables | 688 |
| No aplicables | 1667 |

El resumen general de DQD muestra 2355 controles sin fallo (99,2%); incluye los no aplicables. **Ese porcentaje no demuestra que la base este lista para investigacion.** Muchos controles no aplican porque los dominios estan vacios.

Hallazgos principales:

- Conceptos de diagnosticos, mediciones, unidades, sexo, visitas y procedencia en 0; faltan vocabularios y mapeos validados.
- Controles de completitud por persona en dominios que este prototipo no carga: medicamentos, procedimientos, observaciones y eras.
- Seis `condition_start_date` fuera del encuentro asociado: inicio 2026-10-01 y encuentro 2026-11-09. Revisar la regla que usa onsetDateTime junto con ese visit_occurrence_id; no cambiar las fechas originales solamente para aprobar el control.
- Los valores fuente se conservan, pero su falta de correspondencia a conceptos tambien genera fallos de completitud de mapeo.

Los periodos de observacion se infirieron a partir de los limites temporales de los eventos disponibles. No representan cobertura verificada. La evaluacion usa la estructura del DDL oficial, sin una carga completa de vocabularios ni todas sus restricciones/indices.

## Consultar los resultados

Dashboard oficial: http://localhost:8090

JSON detallado: `output/quality/dqd/results.json`.
Versiones y estado: `output/quality/package-versions.json` y `output/quality/run-status.json`.
Consulta SQL reproducible: `examples/quality.sql`.

La primera evaluacion detecto una referencia incorrecta al esquema de cohortes. Se corrigio a `cohortDatabaseSchema='cdm'` y se repitio DQD: la evaluacion final tiene cero errores SQL. Los logs de la primera ejecucion permanecen en `previous-errors-*` para diagnostico.

Validacion del visor: HTTP 200 en localhost:8090 y proceso Shiny escuchando en su puerto interno 3838. ARES no esta desplegado.

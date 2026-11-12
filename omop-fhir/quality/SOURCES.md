# Fuentes

`OMOPCDM_postgresql_5.4_ddl.sql` se descargo el 2026-11-09 de:
https://raw.githubusercontent.com/OHDSI/CommonDataModel/main/inst/ddl/5.4/postgresql/OMOPCDM_postgresql_5.4_ddl.sql

SHA256: c340fc1723cc71c411aa7d5d67844882ec720bed1135eca2b8a9029d0a3ef854

Proyecto original: https://github.com/OHDSI/CommonDataModel (Apache License 2.0).
El archivo se conserva sin cambios; el preparador sustituye el parametro de esquema.

Imagen de ejecucion: `ohdsi/broadsea-hades:1.19.0`, empleada en el Compose oficial de Broadsea:
https://github.com/OHDSI/Broadsea/blob/main/docker-compose.yml

APIs oficiales:
- https://ohdsi.github.io/Achilles/reference/achilles.html
- https://ohdsi.github.io/DataQualityDashboard/reference/executeDqChecks.html

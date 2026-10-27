# Demo MPI con HAPI FHIR MDM


Proyecto local de demostración de un Master Patient Index (MPI) sobre FHIR R4. Incluye HAPI FHIR JPA Starter con MDM, PostgreSQL y un portal React/TypeScript que consume directamente el API FHIR.

## Qué incluye

* Alta manual de `Patient` y carga de un único JSON FHIR `Patient` por vez.
* Perfil `PatientDO` declarado en `meta.profile`, sin instalar ni forzar la validación de su `StructureDefinition`.
* Reglas MDM en `hapi-fhir/mdm-rules.json` para identificador, nombre, fecha de nacimiento y sexo.
* Consulta de posibles/enlaces MDM, Golden Record, comparación lado a lado, versiones FHIR y los metadatos disponibles de `MDM_LINK`.
* Sin autenticación ni acciones de aceptar, rechazar, fusionar o desvincular.

## Requisitos

* Docker Desktop (Compose v2).
* Para correr el portal fuera de Docker: Node.js 22 o posterior y npm.
* Para abrir y editar cómodamente: VS Code con las extensiones **Docker**, **YAML** y **ESLint** (opcional).

## Ejecución con Docker

Desde la raíz del repositorio:

```powershell
docker compose up --build
```

Abrí:

* Portal: <http://localhost:5173>
* API FHIR: <http://localhost:8080/fhir/metadata>
* Swagger de HAPI: <http://localhost:8080/fhir/swagger-ui/index.html>

La primera ejecución descarga las imágenes y crea el esquema de PostgreSQL; puede tardar algunos minutos. Para detener los servicios, usá `docker compose down`. Los datos persisten en el volumen `postgres-data`. Para reiniciar la demo desde cero, usá `docker compose down -v` (esto elimina los datos locales).

## Recorrido sugerido

1. Importá `examples/reference-patient.json`.
2. Importá `examples/automatic-match-patient.json`: comparte identificador, nombres, nacimiento y sexo; debe producir un enlace `MATCH` según la configuración MDM.
3. Importá `examples/possible-match-patient.json`: comparte nombres, nacimiento y sexo, pero tiene otro identificador; es candidato para revisión (`POSSIBLE_MATCH`).
4. Importá `examples/no-match-patient.json`: no debe generar candidato.

Los resultados dependen del procesamiento asíncrono de MDM. Si un enlace no aparece inmediatamente, recargá o esperá unos segundos y volvé a consultar el Patient.

## Reglas y normalización

HAPI busca las reglas MDM en el classpath. Compose monta `hapi-fhir/mdm-rules.json` en `/app/extra-classes/mpi-mdm-rules.json`, y `mdm_rules_json_location` referencia `mpi-mdm-rules.json`. El nombre distinto evita cargar las reglas predeterminadas de la imagen. Si cambiás el montaje, aplicalo con `docker compose up -d fhir`.

`identifier.system` y `identifier.value` deben coincidir como par. Esta demo fija el sistema `https://mpi.demo.local/cedula` en la regla FHIRPath. Cada valor de `name.given` se trata de manera independiente. Las reglas `STRING` de HAPI comparan texto normalizado; la prueba del portal documenta además la normalización didáctica de acentos, mayúsculas y espacios (`María José` → `MARIA JOSE`).

La configuración de umbrales hace que los cuatro grupos (identificador, nombre, nacimiento y sexo) correspondan al match automático y los dos o tres campos en común se presenten como posibles coincidencias. Revisá y ajustá estos criterios antes de cualquier uso distinto de una demo.

## Pruebas

Para ejecutar las pruebas unitarias del portal:

```powershell
cd portal
npm install
npm test
```

También podés comprobar que el portal compila con `npm run build`.

## Estructura

```
docker-compose.yml          Servicios locales
hapi-fhir/application.yaml Configuración HAPI, PostgreSQL, CORS y MDM
hapi-fhir/mdm-rules.json   Criterios de matching
portal/                    Interfaz React + TypeScript y pruebas
examples/                  Pacientes sintéticos para el recorrido
DESIGN.md                  Diseño técnico breve
```

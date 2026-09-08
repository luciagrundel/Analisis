# Diseño técnico — demo MPI con HAPI FHIR MDM

## Objetivo

Demostración local y didáctica de un índice maestro de pacientes (MPI) sobre FHIR R4. HAPI FHIR JPA Starter persiste los recursos y ejecuta MDM; el portal no contiene un backend propio y llama al API FHIR REST directamente.

## Componentes

```
Navegador (React + TypeScript :5173)
             │ REST FHIR R4
             ▼
HAPI FHIR JPA Starter + MDM (:8080/fhir) ─── PostgreSQL 16
```

* `docker-compose.yml` inicia PostgreSQL, HAPI FHIR 8.10.0-3 y el portal.
* `hapi-fhir/application.yaml` configura FHIR R4, PostgreSQL, CORS local, suscripciones y MDM.
* `hapi-fhir/mdm-rules.json` declara los `matchFields` y el `matchResultMap` de HAPI para `Patient`: identificador, nombres, fecha de nacimiento y sexo.
* `portal/` crea e importa un `Patient`, consulta enlaces con `$mdm-query-links`, recupera el Golden Record y muestra ambos lados.

## Reglas de matching

Cada coincidencia de identificador compara el par `identifier.system` + `identifier.value`. Los elementos de `name.given` se procesan individualmente. HAPI MDM normaliza texto en sus reglas de cadena; los datos de ejemplo incluyen variaciones de acentos, mayúsculas y espacios para mostrar el caso.

La configuración usa los cuatro grupos de datos para `MATCH` y enumera combinaciones de dos o tres grupos como candidatos `POSSIBLE_MATCH` para revisión. El sistema de identificador de la demo es `https://mpi.demo.local/cedula`; el FHIRPath compara únicamente valores que pertenecen a ese sistema. No se habilitan operaciones de aceptación, rechazo, merge ni unlink.

## Historial

El portal solicita `Patient/{id}/_history` para las versiones FHIR del paciente. También conserva y presenta los metadatos disponibles en la respuesta de `$mdm-query-links` (estado del enlace, Golden Record y fechas si el servidor las informa). HAPI expone los enlaces MDM actuales; no fabrica una auditoría histórica propia de enlaces.

## Perfil

Cada recurso del portal declara `meta.profile` con `PatientDO`. No se instala ni se fuerza la validación del `StructureDefinition`, según lo acordado.

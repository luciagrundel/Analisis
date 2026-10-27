# Aprender CQL dentro de HAPI FHIR

Laboratorio local con Docker, HAPI FHIR `v8.12.0-1`, FHIR R4 y pacientes ficticios. El objetivo es leer una regla, ejecutarla sobre un paciente y entender su resultado. Las reglas son didacticas, no recomendaciones clinicas.

## Puesta en marcha en Windows

Requisitos: Docker Desktop iniciado con contenedores Linux y PowerShell. No necesitas Java ni Maven locales. La primera ejecucion descarga la imagen y el arranque puede demorar unos minutos.

Desde PowerShell:

```powershell
cd D:\CQL_prueba
docker compose up -d
powershell -ExecutionPolicy Bypass -File .\scripts\demo.ps1
```

`ExecutionPolicy Bypass` se aplica solo a ese proceso. El script espera al servidor, carga los datos, empaqueta el CQL en una Library, evalua tres pacientes y comprueba 15 resultados. Guarda las respuestas completas en `output/`.

Servidor: http://localhost:8080/fhir/metadata. Los archivos de datos se pueden cargar repetidamente porque usan PUT con identificadores estables.

```powershell
docker compose logs --tail 100 hapi
docker compose stop
docker compose start
# Para retirar el contenedor del laboratorio:
docker compose down
```

La base H2 vive en memoria: al reiniciar el servidor se pierden los recursos. Ejecuta nuevamente `demo.ps1` para recuperarlos.

## Que hace cada pieza

1. **FHIR** define recursos como Patient, Observation y Library.
2. **HAPI FHIR** recibe las peticiones REST y almacena los recursos.
3. **Clinical Reasoning** conecta las operaciones del servidor con el traductor y el motor CQL. Se habilita con `hapi.fhir.cr.enabled: true`.
4. **CQL** contiene las expresiones de la regla. El traductor genera ELM, una representacion que puede ejecutar el motor.
5. **Library** transporta el texto CQL en `content`, codificado en Base64. Guardarla no equivale a evaluar las reglas.
6. **Library/$evaluate** ejecuta la biblioteca en el contexto del paciente enviado como `subject` y devuelve un recurso Parameters.

Flujo: texto CQL → Library → peticion `$evaluate` → traduccion a ELM y consulta de datos del paciente → resultados Parameters. El motor puede reutilizar traducciones en cache.

La ejecucion se solicita explicitamente: guardar una Observation no dispara automaticamente estas reglas.

## Recorrido por los ejemplos

Abri `cql/ReglasBasicas.cql` junto con `data/pacientes.json`.

- **Edad y EsAdulto:** usan birthDate y la fecha fija 2026-01-01. La fecha fija evita que los ejemplos cambien con el calendario.
- **ObservacionesFinales:** consulta Observation en `context Patient` y filtra por estado final. `.value` extrae el valor de los tipos primitivos FHIR; no es el campo valueQuantity de la observacion.
- **AdultoConObservaciones:** combina dos expresiones booleanas con `and`.

| Paciente | Edad | EsAdulto | CantidadObservacionesFinales | AdultoConObservaciones |
|---|---:|---|---:|---|
| Ana | 36 | true | 1 | true |
| Bruno | 15 | false | 1 | false |
| Carla | 40 | true | 0 | false |

Carla tiene una observacion, pero su estado es preliminary. Las observaciones de Ana y Bruno no deben contarse para Carla: esto permite comprobar el contexto de paciente.

La consulta no filtra por codigo, valor ni fecha de la observacion. No representa un indicador clinico; ensena recuperacion de recursos y composicion de reglas.

## CarePlan y PlanDefinition

El proyecto ya incluye un segundo paso posterior a la evaluacion de la regla: el `PlanDefinition` aplica la condicion clinica y genera un `CarePlan`.

- `cql/PlanSeguimiento.cql`: define la expresion `RequiereSeguimiento` reutilizando `Basicas."AdultoConObservaciones"`.
- `data/plan-seguimiento.json`: contiene un `PlanDefinition` con `library` y una accion titulada `Revisar las observaciones finales`.
- `scripts/demo.ps1`: carga la `Library` de seguimiento, valida `Library/plan-seguimiento/$evaluate` y luego ejecuta `PlanDefinition/plan-seguimiento/$apply`.

El flujo es:

1. La `Library` de seguimiento evalua la regla y devuelve un parametro `RequiereSeguimiento`.
2. El `PlanDefinition` usa esa expresion como condicion de aplicabilidad.
3. Si la condicion es `true`, HAPI devuelve un `CarePlan` con un `RequestGroup` contenido y una accion asociada.
4. Si la condicion es `false`, el CarePlan se crea sin acciones de seguimiento.

Los resultados esperados para los tres pacientes son:

- Ana: `RequiereSeguimiento = true`, una accion en el CarePlan.
- Bruno: `RequiereSeguimiento = false`, sin acciones.
- Carla: `RequiereSeguimiento = false`, sin acciones.

Los archivos en `output/` resultantes se llaman `ana-careplan.json`, `bruno-careplan.json` y `carla-careplan.json`.

## Ejecutar manualmente

Despues de cargar los datos, usa `ejemplos.http` con un cliente compatible, o PowerShell:

```powershell
$body = '{"resourceType":"Parameters","parameter":[{"name":"subject","valueString":"Patient/ana"}]}'
Invoke-RestMethod -Method Post `
  -Uri 'http://localhost:8080/fhir/Library/reglas-basicas/$evaluate' `
  -ContentType 'application/fhir+json' -Body $body |
  ConvertTo-Json -Depth 30
```

Las comillas simples en la URL evitan que PowerShell interprete `$evaluate` como variable. Busca parametros como `EsAdulto` con `valueBoolean: true`. Tambien pueden aparecer el paciente y la lista de observaciones.

## Ejercicios

1. Cambia `>= 18` por `>= 40` en CQL. Carga con `powershell -ExecutionPolicy Bypass -File .\scripts\demo.ps1 -SoloCargar` y evalua manualmente. Ana deja de cumplir EsAdulto; Carla sigue cumpliendo. El modo normal del script conserva los resultados originales y detectara el cambio.
2. Cambia la observacion de Carla a `final` en el JSON y vuelve a cargar. Su cantidad pasa a 1 y AdultoConObservaciones pasa a true.
3. Agrega una expresion `define "SinObservacionesFinales": not "TieneObservacionesFinales"`, carga y observa el nuevo parametro de salida.
4. Quita birthDate de un paciente. Piensa por que una edad desconocida puede producir null en vez de false. CQL distingue false de informacion desconocida.

Restaura los cambios para volver a ejecutar las comprobaciones originales. Si una modificacion del CQL no se refleja, reinicia HAPI y vuelve a cargar para descartar cache.

## Archivos

- `compose.yaml`: servidor Docker con puerto publicado solo en localhost.
- `config/application.yaml`: FHIR R4, base temporal y Clinical Reasoning.
- `cql/ReglasBasicas.cql`: reglas editables basicas.
- `cql/PlanSeguimiento.cql`: regla de seguimiento que reutiliza las basicas.
- `data/pacientes.json`: transaccion con tres pacientes y tres observaciones.
- `data/plan-seguimiento.json`: PlanDefinition que aplica la condicion de seguimiento.
- `scripts/demo.ps1`: carga, evaluacion y comprobacion de resultados del CarePlan.
- `ejemplos.http`: peticiones para explorar la API.
- `output/*-careplan.json`: resultados de `PlanDefinition/$apply` para cada paciente.

## Problemas frecuentes

- **Puerto 8080 ocupado:** cambia el puerto izquierdo en compose a `8081`; usa `demo.ps1 -BaseUrl http://localhost:8081/fhir` y ajusta el cliente HTTP.
- **Servidor no listo:** revisa `docker compose logs --tail 100 hapi`; se puede ampliar la espera con `-EsperaSegundos 600`.
- **Operacion desconocida:** comprueba que se monto la configuracion y que Clinical Reasoning esta habilitado.
- **Error de traduccion:** revisa el OperationOutcome y los logs; nombres y mayusculas de las expresiones importan.
- **Docker no responde:** abre Docker Desktop y verifica `docker version`.

## Fuentes

- [CQL en HAPI FHIR](https://hapifhir.io/hapi-fhir/docs/clinical_reasoning/cql.html)
- [HAPI FHIR JPA Server Starter](https://github.com/hapifhir/hapi-fhir-jpaserver-starter)
- [Especificacion CQL](https://cql.hl7.org/)
- [Library en FHIR R4](https://hl7.org/fhir/R4/library.html)

Siguiente paso posible: agregar codigos y ValueSets, ampliar el CarePlan con actividades concretas, y mas adelante reutilizar las expresiones en un Measure con `$evaluate-measure`.

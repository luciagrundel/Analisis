# Guía de inicio: trabajar con OMOP y HL7 FHIR

Para comenzar un proyecto que combine OMOP y un servidor HL7 FHIR, te propongo un enfoque práctico: entender primero qué problema resuelve cada tecnología, cómo se relacionan sus modelos de información y cómo construir un primer flujo que permita transformar información clínica FHIR en datos OMOP.

Como ya trabajás con HL7 FHIR, podés utilizar ese conocimiento como punto de partida y concentrarte en aprender los conceptos propios de OMOP.

Mi recomendación es comenzar con un proyecto pequeño, utilizando Patient, Encounter, Condition y Observation, y avanzar luego hacia una arquitectura más completa.

## 1\. Entender qué es OMOP y cómo se diferencia de FHIR

FHIR and OMOP Harmonisation – An Update - Evidentli

HL7 FHIR — Intercambio de información clínica

Es un estándar para representar, consultar e intercambiar información de salud entre sistemas mediante recursos y APIs.

Se utiliza principalmente en la interoperabilidad operativa y asistencial.

OMOP on FHIR | DTSoF

OMOP Common Data Model — Normalización para análisis

Es un modelo común de datos que organiza información clínica longitudinal en tablas estandarizadas, utilizando vocabularios y reglas compartidas.

Está orientado especialmente a investigación observacional, análisis poblacional, estudios de resultados y generación de evidencia.

La idea central es que FHIR facilita el intercambio de datos y OMOP facilita su análisis estandarizado. No son tecnologías competidoras: pueden complementarse dentro de una misma arquitectura.

| Aspecto | HL7 FHIR | OMOP CDM |
| --- | --- | --- |
| Modelo | Recursos clínicos | Tablas relacionales |
| Unidad principal | Resource | Registro asociado a una persona y a un evento |
| Intercambio | API REST, documentos, mensajería | Consultas y procesos de datos |
| Terminología | CodeSystem, ValueSet, ConceptMap | Vocabularios OMOP, conceptos y relaciones |
| Uso frecuente | Interoperabilidad asistencial | Investigación y análisis longitudinal |
| Identificación | Patient.identifier y Patient.id | person\_id y reglas de vinculación |

Un concepto importante: OMOP no es un servidor FHIR ni una API de interoperabilidad. Es principalmente un modelo de datos. Se puede implementar sobre PostgreSQL u otro motor de base de datos compatible.

## 2\. Arquitectura básica para integrar ambas tecnologías

Para comenzar, te recomiendo una arquitectura unidireccional FHIR → OMOP, manteniendo separados los datos clínicos operativos y el repositorio analítico.

Arquitectura conceptual inicial. Los servicios de terminología apoyan el proceso ETL; no sustituyen las reglas de transformación.

En esta propuesta, el servidor FHIR contiene los recursos clínicos. Un proceso ETL (Extract, Transform, Load) los consulta, interpreta y transforma. Finalmente, guarda la información en tablas OMOP, que pueden ser utilizadas para investigación y análisis.

No recomiendo comenzar con sincronización bidireccional. Convertir OMOP nuevamente a FHIR plantea desafíos adicionales, porque ambos modelos tienen finalidades y estructuras distintas.

## 3\. Conocer el modelo de datos OMOP

La versión OMOP CDM 5.4 es una referencia apropiada para iniciar, especialmente porque la nueva guía HL7 FHIR-to-OMOP 1.0.0 trabaja con ese modelo.

OMOP Common Data Model

+1

Estos son los componentes que conviene aprender primero:

| Concepto OMOP | ¿Qué representa? | Relación aproximada con FHIR |
| --- | --- | --- |
| PERSON | Persona de la que se registran datos | Patient |
| VISIT\_OCCURRENCE | Atención, visita o internación | Encounter |
| CONDITION\_OCCURRENCE | Diagnóstico, signo o condición | Condition |
| MEASUREMENT | Resultados de mediciones clínicas | Observation |
| OBSERVATION | Información clínica que no corresponde a otras tablas específicas | Observation y otros recursos |
| DRUG\_EXPOSURE | Exposición a medicamentos | MedicationAdministration, MedicationDispense y otras fuentes |
| PROCEDURE\_OCCURRENCE | Procedimientos realizados | Procedure |
| CONCEPT | Conceptos de vocabularios normalizados | Coding, CodeSystem |
| CONCEPT\_RELATIONSHIP | Relaciones entre conceptos | Relaciones y mapeos terminológicos |

Las relaciones son aproximadas: no existe una equivalencia uno a uno entre recursos FHIR y tablas OMOP.

Por ejemplo, un recurso FHIR `Observation` correspondiente a glucosa en sangre normalmente se almacena en `MEASUREMENT`, no en `OBSERVATION` de OMOP.

Esto sucede porque OMOP clasifica los eventos clínicos según su dominio semántico, no exclusivamente según el tipo de recurso FHIR que los transporta.

## 4\. Los conceptos de OMOP que deberías dominar

Hay algunos conceptos que son fundamentales para entender cómo funciona OMOP.

CDM — Common Data Model

Es la estructura normalizada de tablas, campos, relaciones y reglas de representación de la información. Define dónde y cómo se guardan los datos clínicos.

Standardized Vocabularies

Es el conjunto de vocabularios que utiliza OMOP para representar conceptos clínicos. Integra terminologías como SNOMED CT, LOINC y RxNorm, entre otras.

Concept ID

Es el identificador numérico interno de un concepto dentro de los vocabularios OMOP. No es equivalente al código SNOMED o LOINC, aunque puede representarlo.

Standard Concept y Source Concept

OMOP conserva el concepto original de la fuente y utiliza, cuando existe, un concepto estandarizado para permitir comparaciones entre bases de datos.

Domain

Es la categoría semántica de un concepto: Condition, Measurement, Drug, Procedure, Observation, etc. Ayuda a determinar la tabla de destino del dato.

Cohort

Es un conjunto de personas que cumplen criterios definidos. Por ejemplo, pacientes con diagnóstico de diabetes que tuvieron una medición de HbA1c durante determinado período.

### Un ejemplo para comprender el mapeo terminológico

Supongamos que un paciente tiene un diagnóstico codificado mediante CIE-10.

Código de origen

CIE-10: E11.9

Diabetes mellitus tipo 2 sin complicaciones (ICD-10-CM)

Mapeo mediante vocabularios OMOP

Source Concept ID

## 35206882

Concepto de origen

Standard Concept ID

## 201826

Concepto estandarizado

Dominio Condition

CONDITION\_OCCURRENCE

condition\_source\_concept\_id · condition\_concept\_id

Ejemplo documentado por OHDSI para ICD-10-CM E11.9.

The echidna.fhir.org Terminology Server

Este ejemplo ilustra una diferencia importante respecto de FHIR: el dato clínico no se almacena solamente con el sistema y código de origen, sino que se vincula a un vocabulario estandarizado mediante relaciones de mapeo.

Para practicar, te recomiendo revisar [Athena de OHDSI](<https://athena.ohdsi.org/?utm_source=chatgpt.com>), que permite buscar conceptos, conocer su dominio, identificar si son estándar y explorar sus relaciones.

ohdsi.github.io

## 5\. Primer ejercicio práctico: transformar un Observation FHIR a OMOP

Te propongo trabajar con un caso de laboratorio porque permite entender tanto el modelo de datos como el rol de la terminología.

### Paso A. Crear un Observation en FHIR

Paciente con una medición de glucosa de 110 mg/dL.

json

```json

{
  "resourceType": "Observation",
  "id": "glucosa-001",
  "status": "final",
  "category": [{
    "coding": [{
      "system": "http://terminology.hl7.org/CodeSystem/observation-category",
      "code": "laboratory"
    }]
  }],
  "code": {
    "coding": [{
      "system": "http://loinc.org",
      "code": "2345-7",
      "display": "Glucose [Mass/volume] in Serum or Plasma"
    }]
  },
  "subject": {
    "reference": "Patient/paciente-001"
  },
  "effectiveDateTime": "2026-11-09T09:00:00-03:00",
  "valueQuantity": {
    "value": 110,
    "unit": "mg/dL",
    "system": "http://unitsofmeasure.org",
    "code": "mg/dL"
  }
}
```

### Paso B. Comprender cómo se almacenaría en OMOP

El recurso FHIR `Observation` se convierte en un registro de la tabla `MEASUREMENT`.

| Campo OMOP | Valor o regla |
| --- | --- |
| measurement\_id | Identificador único del registro |
| person\_id | Identificador interno OMOP del paciente |
| measurement\_concept\_id | Concepto OMOP estándar correspondiente a LOINC 2345-7 |
| measurement\_date | 2026-11-09 |
| measurement\_type\_concept\_id | Concepto que representa la procedencia o tipo de registro |
| value\_as\_number | 110 |
| unit\_concept\_id | Concepto OMOP de mg/dL |
| measurement\_source\_value | 2345-7 |
| measurement\_source\_concept\_id | Concepto OMOP correspondiente al código de origen |

También deberán completarse los campos obligatorios según el CDM y las reglas de la ETL.

Puntos de aprendizaje:

- FHIR utiliza `subject.reference`; OMOP utiliza `person_id`.
- El código LOINC se relaciona con un `concept_id` de OMOP.
- El valor 110 pasa a `value_as_number`.
- La unidad mg/dL también requiere mapeo.
- Debe preservarse la trazabilidad al recurso FHIR original.

Un objetivo inicial razonable sería transformar 10 pacientes, sus atenciones, diagnósticos y resultados de laboratorio, verificando que puedan consultarse correctamente desde ambas plataformas.

## 6\. Herramientas para empezar

| Herramienta | Para qué la utilizaría |
| --- | --- |
| HAPI FHIR | Servidor FHIR para datos de prueba |
| PostgreSQL | Base de datos para implementar OMOP CDM |
| Python | Proceso ETL de FHIR hacia OMOP |
| Athena | Explorar y descargar vocabularios OMOP |
| WhiteRabbit / RabbitInAHat | Analizar fuentes y documentar transformaciones |
| Usagi | Apoyar el mapeo de códigos de origen a conceptos OMOP |
| DataQualityDashboard | Evaluar la calidad de la base OMOP |
| ATLAS | Construir cohortes y realizar análisis sobre datos OMOP |

OHDSI proporciona herramientas de ETL, vocabularios y validación que pueden aprovecharse sin construir todo desde cero.

OHDSI

+2

Para un primer prototipo utilizaría HAPI FHIR, PostgreSQL, Python y Athena. Incorporaría ATLAS y las demás herramientas en una segunda etapa, una vez que los datos estén correctamente transformados.

## 7\. Plan recomendado de aprendizaje e implementación

Te propongo dividir el inicio en cuatro semanas, combinando aprendizaje conceptual con ejercicios técnicos.

1. Semana 1 — Comprender OMOP
   Estudiar el CDM, sus tablas principales, dominios, conceptos estándar y relaciones terminológicas.
   Entregable: un diagrama que relacione Patient, Encounter, Condition y Observation con las tablas OMOP.
2. Semana 2 — Construir el ambiente
   Instalar PostgreSQL con el esquema OMOP CDM 5.4, configurar HAPI FHIR y explorar vocabularios con Athena.
   Entregable: dos repositorios funcionales con datos sintéticos y un conjunto inicial de vocabularios.
3. Semana 3 — Implementar la transformación
   Consultar recursos FHIR mediante API, definir reglas de mapeo e implementar una ETL inicial para PERSON, VISIT\_OCCURRENCE, CONDITION\_OCCURRENCE y MEASUREMENT.
   Entregable: primer flujo FHIR → OMOP funcionando.
4. Semana 4 — Validar y analizar
   Verificar integridad referencial, vocabularios, unidades, fechas, duplicados y trazabilidad. Realizar consultas SQL de análisis.
   Entregable: un caso de uso completo, documentado y validado.

## 8\. Recomendaciones importantes para el proyecto

Hay algunas decisiones de arquitectura que conviene tomar desde el comienzo.

Identidad del paciente. Definir cómo se relacionan `Patient.id`, los identificadores clínicos y `person_id`. OMOP no reemplaza al MPI. Si los datos provienen de varios servidores FHIR, hay que resolver la identidad antes de consolidar registros longitudinales.

Terminología. No asumir que todos los códigos FHIR pueden pasar directamente a OMOP. Hay que revisar el concepto de origen, su correspondencia estándar, dominio, unidades y posibles mapeos faltantes. Esto es especialmente importante con terminologías nacionales.

Trazabilidad y actualizaciones. Registrar la relación entre cada recurso FHIR, su versión y las filas OMOP generadas. Definir cómo se procesan actualizaciones, correcciones, eliminaciones y recargas sin duplicar eventos.

Calidad y privacidad. Trabajar inicialmente con datos sintéticos. En producción, establecer mecanismos de seudonimización, control de acceso y tratamiento adecuado de fechas y otros identificadores.

Finalidad analítica. Definir qué investigaciones o consultas se quieren resolver. Eso permitirá priorizar los recursos y campos que realmente necesitan transformarse.

## 9\. Documentación que recomiendo estudiar

Estos recursos están ordenados según el recorrido de aprendizaje.

Chapter 5 Standardized Vocabularies | The Book of OHDSI

[The Book of OHDSI, segunda edición](<https://ohdsi.github.io/BookOfOhdsi-2ndEdition/?utm_source=chatgpt.com>)

Es el mejor punto de partida conceptual para comprender el ecosistema OHDSI, el modelo OMOP, los vocabularios y los análisis observacionales.

Self-Service RDW

[OMOP Common Data Model 5.4](<https://ohdsi.github.io/CommonDataModel/cdm54.html?utm_source=chatgpt.com>)

Referencia técnica de tablas, campos, relaciones, tipos de datos y convenciones de carga.

[HL7 Vulcan FHIR to OMOP IG 1.0.0](<https://www.hl7.org/fhir/uv/omop/en/index.html?utm_source=chatgpt.com>)

Especialmente relevante para tu proyecto. Publicada en 2026, proporciona patrones, principios y ejemplos para transformar recursos FHIR a OMOP CDM 5.4. La versión 1.0.0 se basa en FHIR R5 y tiene carácter informativo.

FHIR to OMOP FHIR IG v1.0.0

Echidna Browser

[FHIR to OMOP: guía práctica de Echidna](<https://fhir.ohdsi.org/docs/fhir-to-omop/quickstart?utm_source=chatgpt.com>)

Permite entender el proceso de traducción terminológica utilizando operaciones FHIR como `$translate` y `$lookup`. Incluye ejemplos para R4 y R5.

The echidna.fhir.org Terminology Server

## 10\. Primer objetivo que te recomendaría

Empezaría con un prototipo FHIR → OMOP para datos de laboratorio que permita demostrar todo el recorrido:

Pregunta que debería poder resolver el prototipo

¿Cuántos pacientes con diagnóstico de diabetes tuvieron una medición de glucosa superior a determinado valor durante los últimos seis meses?

Para responderla se necesitaría relacionar pacientes, encuentros, diagnósticos, mediciones y conceptos clínicos, poniendo a prueba los aspectos esenciales de ambos modelos.

A partir de ahí, se podría evolucionar hacia cohortes, análisis epidemiológicos, indicadores clínicos e integración de información de varios prestadores.

Mi propuesta es que avancemos en dos líneas paralelas: aprender el modelo OMOP desde sus conceptos fundamentales y construir un laboratorio técnico reproducible con HAPI FHIR, PostgreSQL y una ETL sencilla. Esto te permitiría comprender no solo cómo integrar ambas tecnologías, sino también por qué se toman determinadas decisiones de modelado.

Hay una pregunta que ayudaría a orientar las siguientes etapas: ¿en tu proyecto se busca principalmente extraer información de un servidor FHIR y transformarla a OMOP para análisis, o también se pretende exponer los datos que ya existen en OMOP a través de un servidor FHIR? La arquitectura y las herramientas varían bastante según la dirección del intercambio.

Si quieres, puedo:

- Expand on ETL best practices and challenges
- Describe how to validate and audit the OMOP database post-transformation
- Suggest sample SQL queries for analyzing transformed OMOP data
library ReglasBasicas version '1.0.0'

using FHIR version '4.0.1'

// Fecha fija para obtener los mismos resultados cualquier dia.
parameter FechaEvaluacion Date default @2026-01-01

context Patient

define "Edad":
  years between Patient.birthDate.value and FechaEvaluacion

define "EsAdulto":
  "Edad" >= 18

// .value extrae el valor de un tipo primitivo FHIR.
// El contexto Patient restringe la consulta al paciente evaluado.
define "ObservacionesFinales":
  [Observation] O
    where O.status.value = 'final'

define "CantidadObservacionesFinales":
  Count("ObservacionesFinales")

define "TieneObservacionesFinales":
  exists("ObservacionesFinales")

define "AdultoConObservaciones":
  "EsAdulto" and "TieneObservacionesFinales"

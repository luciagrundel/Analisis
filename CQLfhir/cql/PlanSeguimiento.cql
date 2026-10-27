library PlanSeguimiento version '1.0.0'

using FHIR version '4.0.1'

include ReglasBasicas version '1.0.0' called Basicas

context Patient

// Ejemplo didactico: reutiliza las reglas y la fecha fija de ReglasBasicas.
// PlanDefinition/$apply usa este booleano para incluir o excluir la accion.
define "RequiereSeguimiento":
  Basicas."AdultoConObservaciones"

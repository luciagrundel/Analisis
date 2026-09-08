Creá un proyecto de demostración didáctica de MPI usando HAPI FHIR MDM.

Tecnologías:
- FHIR R4.
- HAPI FHIR actual con MDM.
- Java/Spring Boot para el servidor HAPI.
- PostgreSQL.
- React + TypeScript para el portal.
- Docker Compose para ejecutar todo localmente.

Alcance MVP:
- Cargar Patient manualmente desde el portal.
- Importar uno o varios recursos Patient desde JSON FHIR.
- El portal consume directamente el servidor FHIR.
- Mostrar posibles matches, matches confirmados, comparación lado a lado,
  Golden Record/MDM_LINK e historial disponible.
- Sin autenticación, roles ni requisitos de seguridad: solo desarrollo.
- No habilitar todavía acciones de aceptar, rechazar, fusionar o desvincular.

Perfil Patient:
- Usar FHIR R4 y el perfil:
  https://digital.msp.gob.do/fhir/conectaton/StructureDefinition/PatientDO
- Considerar:
  - identifier.system + identifier.value
  - name.given
  - name.family
  - extensión SegundoApellidoDO:
    https://digital.msp.gob.do/fhir/conectaton/StructureDefinition/SegundoApellidoDO
  - birthDate
  - gender

Reglas:
- Match automático: coinciden nombre, fecha de nacimiento, sexo e identificador.
- Posible match: coinciden dos o tres de esos campos.
- Las reglas deben estar configuradas en mdm-rules.json.
- Normalizar acentos, mayúsculas y espacios para comparación de nombres.

Estructura esperada:
- docker-compose.yml
- hapi-fhir/application.yaml
- hapi-fhir/mdm-rules.json
- portal/
- examples/ con pacientes sintéticos para match automático, posible match y sin match
- README.md con instrucciones para VS Code y ejecución local.

Primero creá un diseño técnico breve y luego implementá el proyecto.
# Estado de verificacion

- JSON de datos leido correctamente: tres Patient y tres Observation.
- Script PowerShell analizado sin errores de sintaxis.
- `docker compose config` valido para la estructura del laboratorio.
- Etiqueta `hapiproject/hapi:v8.12.0-1` comprobada en el registro oficial: https://hub.docker.com/r/hapiproject/hapi/tags

La prueba de integracion queda pendiente: Docker Desktop informa la version del motor, pero las llamadas a listado de imagenes, informacion e inicio de Compose quedaron sin respuesta. La peticion a `http://localhost:8080/fhir/metadata` agoto el tiempo de espera.

Los resultados del README son los esperados por las reglas, no resultados observados en una ejecucion completada. Una vez que Docker responda, ejecutar:

```powershell
docker compose up -d
powershell -ExecutionPolicy Bypass -File .\scripts\demo.ps1
```

El script solo informa exito cuando las 15 comprobaciones contra las respuestas reales de HAPI pasan.

-- Ejecutar despues de la ETL. Esquema educativo; no CDM completo.
SELECT 'person' AS tabla, COUNT(*) FROM person
UNION ALL SELECT 'visit_occurrence', COUNT(*) FROM visit_occurrence
UNION ALL SELECT 'condition_occurrence', COUNT(*) FROM condition_occurrence
UNION ALL SELECT 'measurement', COUNT(*) FROM measurement;

-- Cohorte al 09/11/2026: resultado esperado p5 y p6, 130 y 140 mg/dL.
SELECT p.person_source_value, MAX(m.value_as_number) AS max_glucosa_mg_dl
FROM person p JOIN measurement m USING (person_id)
WHERE m.measurement_source_value = '2345-7'
  AND m.unit_source_value = 'mg/dL'
  AND m.measurement_date BETWEEN '2026-05-09' AND '2026-11-09'
  AND m.value_as_number > 125
  AND EXISTS (
    SELECT 1 FROM condition_occurrence c
    WHERE c.person_id = p.person_id AND c.condition_source_value = 'E11.9'
      AND c.condition_start_date <= '2026-11-09'
  )
GROUP BY p.person_source_value ORDER BY p.person_source_value;

-- Trazabilidad de FHIR a OMOP.
SELECT source, resource_key, target_table, target_id, version
FROM provenance ORDER BY resource_key;

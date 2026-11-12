-- Ejecutar despues de quality all.
-- Estadisticas Achilles: total de personas y analisis con filas de resultados.
SELECT * FROM achilles_results.achilles_results WHERE analysis_id = 1;
SELECT COUNT(*) AS filas_resultado, COUNT(DISTINCT analysis_id) AS analisis_con_resultados
FROM achilles_results.achilles_results;

-- Un control que no aplica no demuestra calidad de datos.
SELECT COUNT(*) AS controles,
       SUM(is_error) AS errores_ejecucion,
       SUM(failed) AS fallidos,
       SUM(passed) AS aprobados,
       SUM(not_applicable) AS no_aplican
FROM dqd_results.dqdashboard_results;

SELECT cdm_table_name, check_name, cdm_field_name,
       num_violated_rows, num_denominator_rows, pct_violated_rows,
       threshold_value, error
FROM dqd_results.dqdashboard_results
WHERE failed = 1 OR is_error = 1
ORDER BY is_error DESC, cdm_table_name, check_name, cdm_field_name;

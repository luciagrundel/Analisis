path <- '/output/dqd/results.json'
if (!file.exists(path)) stop('Ejecutar primero quality dqd para generar results.json')
DataQualityDashboard::viewDqDashboard(jsonPath = path,
  launch.browser = FALSE, host = '0.0.0.0', port = 3838)

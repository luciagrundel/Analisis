options(warn = 1)
dir.create('/output/achilles', recursive = TRUE, showWarnings = FALSE)
dir.create('/output/dqd', recursive = TRUE, showWarnings = FALSE)
dir.create('/output/jdbc', recursive = TRUE, showWarnings = FALSE)
Sys.setenv(DATABASECONNECTOR_JAR_FOLDER = '/output/jdbc')
required <- c('Achilles', 'DataQualityDashboard', 'DatabaseConnector', 'jsonlite')
missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing)) stop(paste('Missing packages:', paste(missing, collapse = ', ')))
versions <- vapply(required, function(p) as.character(packageVersion(p)), character(1))
writeLines(capture.output(sessionInfo()), '/output/sessionInfo.txt')
jsonlite::write_json(as.list(versions), '/output/package-versions.json', auto_unbox = TRUE, pretty = TRUE)
DatabaseConnector::downloadJdbcDrivers('postgresql', pathToDriver = '/output/jdbc')
details <- DatabaseConnector::createConnectionDetails(
  dbms = 'postgresql', server = 'omop-db/omop', port = 5432,
  user = 'omop', password = Sys.getenv('PGPASSWORD'), pathToDriver = '/output/jdbc')
mode <- commandArgs(trailingOnly = TRUE)
if (!length(mode)) mode <- 'all'
if (!mode %in% c('all', 'achilles', 'dqd')) stop('Mode must be all, achilles or dqd')
statuses <- if (file.exists('/output/run-status.json')) jsonlite::read_json('/output/run-status.json', simplifyVector = FALSE) else list()
runStep <- function(name, code) {
  cat('Starting:', name, '\n')
  started <- format(Sys.time(), tz = 'UTC', usetz = TRUE)
  outcome <- tryCatch({ force(code); list(status = 'completed') },
                      error = function(e) list(status = 'error', message = conditionMessage(e)))
  outcome$startedAt <- started
  outcome$finishedAt <- format(Sys.time(), tz = 'UTC', usetz = TRUE)
  statuses[[name]] <<- outcome
  jsonlite::write_json(statuses, '/output/run-status.json', auto_unbox = TRUE, pretty = TRUE)
  if (outcome$status == 'error') cat(name, 'ERROR:', outcome$message, '\n')
}
if (mode %in% c('all', 'achilles')) {
  runStep('achilles', Achilles::achilles(connectionDetails = details,
    cdmDatabaseSchema = 'cdm', resultsDatabaseSchema = 'achilles_results',
    scratchDatabaseSchema = 'scratch', vocabDatabaseSchema = 'cdm',
    tempEmulationSchema = 'scratch', sourceName = 'FHIR synthetic laboratory',
    cdmVersion = '5.4', smallCellCount = 0, numThreads = 1,
    outputFolder = '/output/achilles', verboseMode = FALSE))
}
if (mode %in% c('all', 'dqd')) {
  if (dir.exists('/output/dqd/errors')) {
    file.rename('/output/dqd/errors', paste0('/output/dqd/previous-errors-', format(Sys.time(), '%Y%m%dT%H%M%S')))
  }
  runStep('dqd', DataQualityDashboard::executeDqChecks(connectionDetails = details,
    cdmDatabaseSchema = 'cdm', resultsDatabaseSchema = 'dqd_results',
    cohortDatabaseSchema = 'cdm',
    vocabDatabaseSchema = 'cdm', cdmSourceName = 'FHIR synthetic laboratory',
    cdmVersion = '5.4', numThreads = 1, outputFolder = '/output/dqd',
    outputFile = 'results.json', writeToTable = TRUE, verboseMode = FALSE))
}
if (any(vapply(statuses, function(s) s$status == 'error', logical(1)))) quit(status = 1)
cat('Completed:', mode, '\n')

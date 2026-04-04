#!/usr/bin/env bash

AIRFLOW_HOME="$(pwd)"
export AIRFLOW_HOME
PYTHONPATH="$(pwd)"
export PYTHONPATH

airflow db migrate
airflow users create \
  --username admin \
  --password admin \
  --firstname admin \
  --lastname admin \
  --role Admin \
  --email admin@example.com

airflow api-server --port 8080 &
airflow scheduler &
airflow dag-processor &
airflow triggerer &

wait
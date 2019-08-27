FROM puckel/docker-airflow:1.10.4

COPY --chown=airflow:airflow config/ /usr/local/airflow/config/

ENV PYTHONPATH "${PYTHONPATH}:/usr/local/airflow"

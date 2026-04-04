import importlib.metadata

from airflow.sdk import DAG, task

with DAG(dag_id='test_hello_v1', ) as dag:
    @task
    def hello():
        print("Hello Airflow!")


    @task
    def print_distributions():
        for dist in importlib.metadata.distributions():
            print(f"{dist.metadata['Name']}=={dist.version}")


    # noinspection PyStatementEffect
    hello() >> print_distributions()

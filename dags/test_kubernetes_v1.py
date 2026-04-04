from airflow.sdk import DAG, task
from kubernetes import client, config, watch

with DAG(dag_id='test_hello_v1', ) as dag:
    @task
    def list_pods():
        config.load_kube_config()

        v1 = client.CoreV1Api()
        print("Listing pods with their IPs:")
        ret = v1.list_pod_for_all_namespaces(watch=False)
        for i in ret.items:
            print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))


    @task
    def watch_namespaces():
        config.load_kube_config()

        v1 = client.CoreV1Api()
        count = 10
        watcher = watch.Watch()
        for event in watcher.stream(v1.list_namespace, _request_timeout=60):
            print("Event: %s %s" % (event['type'], event['object'].metadata.name))
            count -= 1
            if not count:
                watcher.stop()

        print("Ended.")


    list_pods() >> watch_namespaces()

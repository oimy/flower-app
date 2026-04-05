from airflow.exceptions import AirflowFailException, AirflowSkipException
from airflow.sdk import DAG, task
from kubernetes import client, config, watch
from kubernetes.client import ApiException
from kubernetes.config import ConfigException

RESOURCES = [
    {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "authezat-ui",
            "namespace": "authezat"
        },
        "spec": {
            "replicas": 2,
            "selector": {
                "matchLabels": {
                    "app": "authezat-ui"
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": "authezat-ui"
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": "authezat-container",
                            "image": "oimd/soia-authezat-ui:v20260405T010125",
                            "imagePullPolicy": "IfNotPresent",
                        }
                    ]
                },
            },
        },
    },
    {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "authezat-ui",
            "namespace": "authezat"
        },
        "spec": {
            "type": "NodePort",
            "selector": {
                "app": "authezat-ui"
            },
            "ports": [
                {
                    "protocol": "TCP",
                    "port": 80,
                    "targetPort": 80,
                    "nodePort": 30411
                }
            ],
        },
    },
]

with DAG(dag_id='cd_authezat_ui_v1', tags={"ci", "authezat"}) as dag:
    @task(multiple_outputs=True)
    def load_resources():
        deployment_dict = dict()
        service_dict = dict()

        for resource in RESOURCES:
            if not (kind := resource.get("kind")):
                raise AirflowFailException(f"kind is not given in {resource}")
            if not (metadata := resource.get("metadata")) or not isinstance(metadata, dict):
                raise AirflowFailException(f"metadata is not given in {resource} or invalid form : {metadata}")
            if not (name := metadata.get("name")):
                raise AirflowFailException(f"name is not given in {metadata}")
            if not (namespace := metadata.get("namespace")):
                raise AirflowFailException(f"namespace is not given in {metadata}")
            base_dict = {
                "name": name,
                "namespace": namespace,
            }

            if kind == "Deployment":
                deployment_dict = {**base_dict, 'body': resource}
            elif kind == "Service":
                service_dict = {**base_dict, 'body': resource}
            else:
                raise AirflowFailException(f"unknown kind {kind}")

        return {
            "deployment": deployment_dict,
            "service": service_dict
        }


    @task
    def apply_deployment(resource_dict: dict):
        name: str = resource_dict["name"]
        namespace: str = resource_dict["namespace"]
        if not (body := resource_dict["body"]):
            raise AirflowSkipException()

        try:
            config.load_incluster_config()
        except ConfigException:
            config.load_kube_config()
        apps = client.AppsV1Api()

        try:
            apps.read_namespaced_deployment(name=name, namespace=namespace)

            print(f"deployment {name} exists. patching...")
            apps.patch_namespaced_deployment(name=name, namespace=namespace, body=body)

        except ApiException as ae:
            if ae.status != 404:
                raise ae

            print(f"deployment {name} not found. creating...")
            apps.create_namespaced_deployment(namespace=namespace, body=body)

        print(f"Waiting for {name} to be ready...")
        watcher = watch.Watch()
        replicas = body.get('spec', {}).get('replicas', 1)
        for event in watcher.stream(
                apps.list_namespaced_deployment,
                namespace=namespace,
                field_selector=f"metadata.name={name}",
                timeout_seconds=300
        ):
            deployment = event['object']
            status = deployment.status
            if (
                    status.updated_replicas == replicas
                    and status.ready_replicas == replicas
                    and status.available_replicas == replicas
            ):
                print(f"deployment {name} is successfully rolled out!")
                watcher.stop()
                return


    @task
    def apply_service(resource_dict: dict):
        name: str = resource_dict["name"]
        namespace: str = resource_dict["namespace"]
        if not (body := resource_dict["body"]):
            raise AirflowSkipException()

        try:
            config.load_incluster_config()
        except ConfigException:
            config.load_kube_config()
        core = client.CoreV1Api()

        try:
            core.read_namespaced_service(name=name, namespace=namespace)

            print(f"service {name} exists. patching...")
            core.patch_namespaced_service(name=name, namespace=namespace, body=body)

        except ApiException as ae:
            if ae.status != 404:
                raise ae

            print(f"service {name} not found. creating...")
            core.create_namespaced_service(namespace=namespace, body=body)


    task_load_resources = load_resources()

    task_apply_deployment = apply_deployment(resource_dict=task_load_resources['deployment'])

    task_apply_service = apply_service(resource_dict=task_load_resources['service'])

    _ = task_load_resources >> [task_apply_deployment, task_apply_service]

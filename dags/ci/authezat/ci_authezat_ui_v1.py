from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.sdk import DAG

from kubernetes.client import models

secret_volume = models.V1Volume(
    name="docker-config",
    secret=models.V1SecretVolumeSource(
        secret_name="flower-dockerhub-secret",
        items=[models.V1KeyToPath(key=".dockerconfigjson", path="config.json")]
    )
)

secret_volume_mount = models.V1VolumeMount(
    name="docker-config",
    mount_path="/kaniko/.docker/config.json",
    sub_path="config.json",
    read_only=True
)

with DAG(dag_id='ci_authezat_ui_v1', tags={"ci", "authezat"}) as dag:
    task_build_image = KubernetesPodOperator(
        task_id='build_image',
        name='kaniko-build-authzat-ui',
        namespace='flower',
        image='gcr.io/kaniko-project/executor:latest',
        volumes=[secret_volume],
        volume_mounts=[secret_volume_mount],
        arguments=[
            "--dockerfile=Dockerfile",
            "--context=git://github.com/oimy/authezat-ui.git#refs/heads/main",
            "--destination=oimd/soia-authezat-ui:latest",
            "--destination=oimd/soia-authezat-ui:v{{ ts_nodash }}",
            "--ignore-path=/product_uuid"
        ]
    )

    task_build_image

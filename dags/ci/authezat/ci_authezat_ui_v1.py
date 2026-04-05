from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.sdk import DAG

from kubernetes.client import models

secret_volume = models.V1Volume(
    name="docker-config",
    secret=models.V1SecretVolumeSource(
        secret_name="flower-app-dockerhub-secret",
        items=[models.V1KeyToPath(key=".dockerconfigjson", path="config.json")]
    )
)

secret_volume_mount = models.V1VolumeMount(
    name="docker-config",
    mount_path="/home/user/.docker/config.json",
    sub_path="config.json",
    read_only=True
)

with DAG(dag_id='ci_authezat_ui_v1', tags={"ci", "authezat", "ui"}) as dag:
    task_build_image = KubernetesPodOperator(
        task_id='build_image',
        name='buildkit-authzat-ui',
        namespace='flower',
        image='moby/buildkit:v0.29.0-rootless',
        env_vars={
            "DOCKER_CONFIG": "/home/user/.docker"
        },
        volumes=[secret_volume],
        volume_mounts=[secret_volume_mount],
        cmds=["rootlesskit", "sh", "-c"],
        arguments=[
            """
            buildkitd --oci-worker-no-process-sandbox &
            while ! buildctl debug workers > /dev/null 2>&1; do sleep 1; done

            buildctl build \
                --frontend=dockerfile.v0 \
                --opt context=https://github.com/oimy/authezat-ui.git#refs/heads/main \
                --opt filename=Dockerfile \
                --output type=image,name=oimd/soia-authezat-ui:v{{ ts_nodash }},push=true \
                --export-cache type=inline \
                --import-cache type=registry,ref=oimd/soia-authezat-ui:build-cache
            """
        ],
    )

    task_build_image

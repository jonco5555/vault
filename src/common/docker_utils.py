from typing import Optional
import docker
import subprocess
import os

DOCKER_RUNTIME_SOCKET = "/var/run/docker.sock"
VOLUMES = {
    f"{DOCKER_RUNTIME_SOCKET}": {"bind": f"{DOCKER_RUNTIME_SOCKET}", "mode": "rw"}
}

def spawn_container(image_name: str, image_tag: str = "latest", command: Optional[str] = None):
    client = docker.from_env()

    # Run a container from the image
    container = client.containers.run(
        f"{image_name}:{image_tag}",  # image name
        command=command,
        detach=True,  # run in background
        volumes=VOLUMES,
    )

    return container

def spawn_and_wait_for_container_to_finish(image_name: str, image_tag: str = "latest", command: Optional[str] = None):
    # Run a container from the image
    container = spawn_container(image_name, image_tag, command)

    # Wait for container to finish and get logs
    container.wait()
    print(container.logs().decode("utf-8"))

    # Optionally remove container
    container.remove()


def _running_in_docker() -> bool:
    return os.path.exists("/.dockerenv")

# NOTE: Should be running inside docker!
def get_self_container_id() -> str:
    if not _running_in_docker():
        raise RuntimeError("Should be running inside a docker scope")
    
    result = subprocess.run(['hostname'], capture_output=True, text=True)
    if 0 != result.returncode:
        raise RuntimeError(f"Got errorcode {result.returncode}")
    return str(result.stdout)[:-1] # no new line

def get_container_address(container_id: str) -> str:
    client = docker.DockerClient(base_url=f'unix:/{DOCKER_RUNTIME_SOCKET}')
    container = client.containers.get(container_id)
    networks = container.attrs['NetworkSettings']['Networks']
    return next(iter(networks.values()))['IPAddress']
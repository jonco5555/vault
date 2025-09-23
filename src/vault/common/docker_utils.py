import asyncio
import os
import subprocess
from typing import Optional

import docker

DOCKER_RUNTIME_SOCKET = "/var/run/docker.sock"
VOLUMES = {
    f"{DOCKER_RUNTIME_SOCKET}": {"bind": f"{DOCKER_RUNTIME_SOCKET}", "mode": "rw"}
}


def spawn_container(
    image_name: str,
    image_tag: str = "latest",
    container_name: Optional[str] = None,
    command: Optional[str] = None,
    network: Optional[str] = None,
    environment: Optional[dict[str, str]] = None,
):
    client = docker.from_env()

    # Run a container from the image
    container = client.containers.run(
        f"{image_name}:{image_tag}",  # image name
        name=container_name,
        command=command,
        detach=True,  # run in background
        volumes=VOLUMES,
        network=network,
        environment=environment,
    )

    return container


def _running_in_docker() -> bool:
    return os.path.exists("/.dockerenv")


# NOTE: Should be running inside docker!
def get_self_container_id() -> str:
    if not _running_in_docker():
        raise RuntimeError("Should be running inside a docker scope")

    result = subprocess.run(["hostname"], capture_output=True, text=True)
    if 0 != result.returncode:
        raise RuntimeError(f"Got errorcode {result.returncode}")
    return str(result.stdout)[:-1]  # no new line


def get_container_address(container_id: str) -> str:
    client = docker.DockerClient(base_url=f"unix:/{DOCKER_RUNTIME_SOCKET}")
    container = client.containers.get(container_id)
    networks = container.attrs["NetworkSettings"]["Networks"]
    return next(iter(networks.values()))["IPAddress"]


def get_container_name(container_id: str) -> str:
    client = docker.DockerClient(base_url=f"unix:/{DOCKER_RUNTIME_SOCKET}")
    container = client.containers.get(container_id)
    return container.name


async def wait_for_container_to_stop(container_id: str, timeout: float | None = None):
    client = docker.from_env()
    container = client.containers.get(container_id)

    async def _wait():
        return await asyncio.to_thread(container.wait)  # non-blocking

    try:
        result = await asyncio.wait_for(_wait(), timeout=timeout)
        print(f"Container {container_id} stopped with:", result)
        return result
    except asyncio.TimeoutError:
        print(f"Timeout while waiting for {container_id} to stop")
        return None


def remove_container(container_id: str):
    client = docker.from_env()
    container = client.containers.get(container_id)

    # TODO: Remove forcibly?
    container.remove(force=False)

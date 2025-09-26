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
    """
    Spawn a Docker container with the specified parameters.

    Args:
        image_name (str): Name of the Docker image.
        image_tag (str, optional): Tag of the Docker image. Defaults to "latest".
        container_name (Optional[str], optional): Name for the container. Defaults to None.
        command (Optional[str], optional): Command to run in the container. Defaults to None.
        network (Optional[str], optional): Docker network to connect to. Defaults to None.
        environment (Optional[dict[str, str]], optional): Environment variables for the container. Defaults to None.

    Returns:
        docker.models.containers.Container: The spawned container object.
    """
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
    """
    Check if the current process is running inside a Docker container.

    Returns:
        bool: True if running inside Docker, False otherwise.
    """
    return os.path.exists("/.dockerenv")


def get_self_container_id() -> str:
    """
    Get the container ID of the current Docker container.
    Should be called only when running inside Docker.

    Returns:
        str: The container ID.

    Raises:
        RuntimeError: If not running inside Docker or if hostname command fails.
    """
    if not _running_in_docker():
        raise RuntimeError("Should be running inside a docker scope")

    result = subprocess.run(["hostname"], capture_output=True, text=True)
    if 0 != result.returncode:
        raise RuntimeError(f"Got errorcode {result.returncode}")
    return str(result.stdout)[:-1]  # no new line


def get_container_address(container_id: str) -> str:
    """
    Get the IP address of a Docker container by its ID.

    Args:
        container_id (str): The container ID.

    Returns:
        str: The IP address of the container.
    """
    client = docker.DockerClient(base_url=f"unix:/{DOCKER_RUNTIME_SOCKET}")
    container = client.containers.get(container_id)
    networks = container.attrs["NetworkSettings"]["Networks"]
    return next(iter(networks.values()))["IPAddress"]


def get_container_name(container_id: str) -> str:
    """
    Get the name of a Docker container by its ID.

    Args:
        container_id (str): The container ID.

    Returns:
        str: The name of the container.
    """
    client = docker.DockerClient(base_url=f"unix:/{DOCKER_RUNTIME_SOCKET}")
    container = client.containers.get(container_id)
    return container.name


async def wait_for_container_to_stop(container_id: str, timeout: float | None = None):
    """
    Wait asynchronously for a Docker container to stop.

    Args:
        container_id (str): The container ID.
        timeout (float | None, optional): Timeout in seconds. Defaults to None.

    Returns:
        dict | None: Result from container.wait() if stopped, None if timeout.
    """
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
    """
    Remove a Docker container by its ID.

    Args:
        container_id (str): The container ID.

    Returns:
        None
    """
    client = docker.from_env()
    container = client.containers.get(container_id)

    # TODO: Remove forcibly?
    container.remove(force=False)

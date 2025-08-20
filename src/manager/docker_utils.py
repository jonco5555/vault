from typing import Optional
import docker

volumes = {
    "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}
}

def spawn_container(image_name: str, image_tag: str = "latest", command: Optional[str] = None):
    client = docker.from_env()

    # Run a container from the image
    container = client.containers.run(
        f"{image_name}:{image_tag}",  # image name
        command=command,
        detach=True,  # run in background
        volumes=volumes,
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
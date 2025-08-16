import docker

def spawn_container(image_name: str, image_tag: str = "latest"):
    client = docker.from_env()

    # Run a container from the image
    container = client.containers.run(
        f"{image_name}:{image_tag}",  # image name
        detach=True  # run in background
    )

    return container

def spawn_and_wait_for_container(image_name: str, image_tag: str = "latest"):
    # Run a container from the image
    container = spawn_container(image_name, image_tag)
    
    # Wait for container to finish and get logs
    container.wait()
    print(container.logs().decode("utf-8"))

    # Optionally remove container
    container.remove()
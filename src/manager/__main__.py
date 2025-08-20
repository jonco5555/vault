from . import docker_utils

if __name__ == "__main__":
    print("hello manager!")
    docker_utils.spawn_and_wait_for_container_to_finish("vault", command="python -m src.bootstrap")
docker rm -f $(docker ps -aq)
docker system prune
docker-compose build

docker-compose up --scale postgres=1 --scale manager=1 --scale user=0 &
sleep 10
docker run --rm -d --network vault-net --name vault-user vault:latest python -m src.vault.user
docker attach vault-user

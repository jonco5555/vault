docker-compose build

docker-compose up &
sleep 10
docker run --rm -d --network vault-net --name vault-user vault:latest python -m src.vault.user
docker attach vault-user
sleep 10
docker-compose down

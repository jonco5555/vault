docker-compose up --build &
sleep 10
docker run --rm -d --network vault-net --name vault-user vault:latest \
    vault user --user-id alice --server-ip vault-manager --server-port 5000 \
    --threshold 3 --num-of-total-shares 3 --ca-cert-path /app/certs/ca.crt
docker attach vault-user
sleep 10
docker-compose down

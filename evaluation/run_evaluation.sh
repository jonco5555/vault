docker-compose build
docker-compose up &
sleep 15
docker run --rm -d --network vault-net --name vault-user vault:latest \
    vault evaluation_user --user-id alice --server-ip vault-manager --server-port 5000 \
    --threshold 3 --num-of-total-shares 3 --ca-cert-path /app/certs/ca.crt
sleep 60
docker-compose down

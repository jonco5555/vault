docker-compose build
docker-compose up -d
sleep 15
docker run --rm -it --network vault-net --name vault-user vault:latest \
    vault evaluation-user --user-id alice --server-ip vault-manager --server-port 5000 \
    --threshold 3 --num-of-total-shares 3 --ca-cert-path /app/certs/ca.crt
docker-compose down

export NUM_SHARE_SERVERS_ENV=3

export TOTAL_SHARES=$((NUM_SHARE_SERVERS_ENV + 1))
docker-compose build
docker-compose up &
sleep 15
docker run --rm -d --network vault-net --name vault-user vault:latest \
    vault user --user-id alice --server-ip vault-manager --server-port 5000 \
    --threshold $TOTAL_SHARES --num-of-total-shares $TOTAL_SHARES --ca-cert-path /app/certs/ca.crt
sleep 20
docker-compose down

python -m grpc_tools.protoc -I=protos --python_out=src/vault/grpc/ --grpc_python_out=src/vault/grpc/ protos/vault.proto

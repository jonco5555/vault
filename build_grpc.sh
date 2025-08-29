python -m grpc_tools.protoc -I=protos --python_out=src/vault/common/generated/ --grpc_python_out=src/vault/common/generated/ protos/vault.proto
python -m grpc_tools.protoc -I=protos --python_out=src/vault/common/generated/ --grpc_python_out=src/vault/common/generated/ protos/setup.proto

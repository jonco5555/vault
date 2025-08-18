from .generated import vault_setup_pb2
from .generated import vault_setup_pb2_grpc

class SetupMaster(vault_setup_pb2_grpc.SetupMaster):
    def __init__(self):
        vault_setup_pb2_grpc.SetupMaster.__init__(self)

    def Register(self, request: vault_setup_pb2.RegisterRequest, context):
        # TODO: store registartion data in db
        return vault_setup_pb2.RegisterResponse(is_registered=True)
from enum import Enum

from pydantic import BaseModel

from vault.common.generated import setup_pb2


class ServiceType(int, Enum):
    SHARE_SERVER = 0
    BOOSTRAP_SERVER = 1


class ServiceData(BaseModel):
    type: ServiceType
    container_id: str
    ip_address: str
    public_key: bytes


def ServiceData_to_SetupRegisterRequest(
    service_data: ServiceData,
) -> setup_pb2.SetupRegisterRequest:
    return setup_pb2.SetupRegisterRequest(
        type=service_data.type,
        container_id=service_data.container_id,
        ip_address=service_data.ip_address,
        public_key=service_data.public_key,
    )


def SetupRegisterRequest_to_ServiceData(
    register_request: setup_pb2.SetupRegisterRequest,
) -> ServiceData:
    return ServiceData(
        type=register_request.type,
        container_id=register_request.container_id,
        ip_address=register_request.ip_address,
        public_key=register_request.public_key,
    )

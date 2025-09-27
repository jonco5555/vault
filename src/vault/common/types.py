from enum import Enum

from pydantic import BaseModel

from vault.common.generated import setup_pb2


class ServiceType(int, Enum):
    SHARE_SERVER = 0
    BOOSTRAP_SERVER = 1


class ServiceData(BaseModel):
    type: ServiceType
    container_id: str
    container_name: str
    public_key: bytes


def ServiceData_to_SetupRegisterRequest(
    service_data: ServiceData,
) -> setup_pb2.SetupRegisterRequest:
    return setup_pb2.SetupRegisterRequest(
        type=service_data.type,
        container_id=service_data.container_id,
        container_name=service_data.container_name,
        public_key=service_data.public_key,
    )


def SetupRegisterRequest_to_ServiceData(
    register_request: setup_pb2.SetupRegisterRequest,
) -> ServiceData:
    return ServiceData(
        type=register_request.type,
        container_id=register_request.container_id,
        container_name=register_request.container_name,
        public_key=register_request.public_key,
    )


class Key(BaseModel):
    x: str
    y: str


class PartialDecryption(BaseModel):
    x: str
    yc1: Key

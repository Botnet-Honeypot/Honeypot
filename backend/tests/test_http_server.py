import pytest
from unittest.mock import create_autospec
from hypothesis import given, strategies as st
import backend.http_server as server
from backend.container import Containers
import grpc
import target_system_provider.target_system_provider_pb2_grpc as tsp
import target_system_provider.target_system_provider_pb2 as messages


@pytest.fixture(scope='module')
def container_handler():
    handler = create_autospec(Containers)
    return handler


@pytest.fixture(scope='module', autouse=True)
def http_server(container_handler: Containers):
    http_server = server.start_http_server(
        container_handler,
        'PUBLIC_ADDRESS',
        bind_address='localhost:50051')
    yield http_server
    http_server.stop(grace=None)


@pytest.fixture(scope='module')
def grpc_channel():
    with grpc.insecure_channel('localhost:50051') as channel:
        yield channel


@given(user=st.text(), password=st.text())
def test_AcquireTargetSystem_no_exceptions(
        grpc_channel: grpc.Channel,
        user: str, password: str):
    stub = tsp.TargetSystemProviderStub(grpc_channel)
    response = stub.AcquireTargetSystem(
        messages.AcquisitionRequest(
            user=user,
            password=password
        ))

    assert response.address == 'PUBLIC_ADDRESS'


@given(id=st.text())
def test_YieldTargetSystem_no_exceptions(
        grpc_channel: grpc.Channel,
        id: str):
    stub = tsp.TargetSystemProviderStub(grpc_channel)
    stub.YieldTargetSystem(
        messages.YieldRequest(id=id))

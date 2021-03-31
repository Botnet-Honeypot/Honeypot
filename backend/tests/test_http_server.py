import pytest
from unittest.mock import ANY, create_autospec, patch
from hypothesis import given, strategies as st
import backend.http_server as server
from backend.container import Containers
import grpc
import target_system_provider.target_system_provider_pb2_grpc as tsp
import target_system_provider.target_system_provider_pb2 as messages


@pytest.fixture(scope='module')
def container_handler():
    return create_autospec(Containers)


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
def test_AcquireTargetSystem(
        container_handler: Containers,
        grpc_channel: grpc.Channel,
        user: str, password: str):
    with patch.object(container_handler, 'format_config', return_value={'ID': 'openssh-server342'}):
        with patch.object(container_handler, 'create_container'):
            with patch.object(container_handler, 'get_container_port', return_value=53245):

                stub = tsp.TargetSystemProviderStub(grpc_channel)
                response = stub.AcquireTargetSystem(
                    messages.AcquisitionRequest(
                        user=user,
                        password=password
                    ))

                container_handler.format_config.assert_called_once_with(
                    ANY, user, password
                )
                container_handler.create_container.assert_called_once()
                container_handler.get_container_port.assert_called_once_with('openssh-server342')

                assert response.id == 'openssh-server342'
                assert response.address == 'PUBLIC_ADDRESS'
                assert response.port == 53245


@given(id=st.text())
def test_YieldTargetSystem(
        container_handler: Containers,
        grpc_channel: grpc.Channel,
        id: str):
    with patch.object(container_handler, 'stop_container'):
        with patch.object(container_handler, 'destroy_container'):
            stub = tsp.TargetSystemProviderStub(grpc_channel)
            stub.YieldTargetSystem(
                messages.YieldRequest(id=id))

            container_handler.stop_container.assert_called_once_with(id)
            container_handler.destroy_container.assert_called_once_with(id)

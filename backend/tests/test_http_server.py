import pytest
from unittest.mock import ANY, create_autospec, patch
from hypothesis import given, strategies as st
import backend.http_server as server
from backend.container import Containers
import grpc
import target_system_provider.target_system_provider_pb2_grpc as tsp
import target_system_provider.target_system_provider_pb2 as messages


@pytest.fixture(scope='module')
def container_handler() -> Containers:
    return create_autospec(Containers)


@pytest.fixture(scope='module', autouse=True)
def http_server(container_handler: Containers) -> grpc.Server:
    http_server = server.start_http_server(
        container_handler,
        False,
        'PUBLIC_ADDRESS',
        bind_address='localhost:50051')
    yield http_server
    http_server.stop(grace=None)


@pytest.fixture(scope='module')
def grpc_channel() -> grpc.Channel:
    with grpc.insecure_channel('localhost:50051') as channel:
        yield channel


@pytest.fixture(scope='module')
def tsp_stub(grpc_channel: grpc.Channel):
    return tsp.TargetSystemProviderStub(grpc_channel)


@given(user=st.text(), password=st.text())
def test_AcquireTargetSystem(
        container_handler: Containers,
        tsp_stub: tsp.TargetSystemProviderStub,
        user: str, password: str):
    with patch.object(container_handler, 'format_config', return_value={'ID': 'openssh-server342'}):
        with patch.object(container_handler, 'create_container'):
            with patch.object(container_handler, 'get_container_port', return_value=53245):

                response = tsp_stub.AcquireTargetSystem(
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


@given(user=st.text(), password=st.text())
def test_YieldTargetSystem(
        container_handler: Containers,
        tsp_stub: tsp.TargetSystemProviderStub,
        user: str, password: str):
    with patch.object(container_handler, 'format_config', return_value={'ID': 'openssh-server342'}):
        with patch.object(container_handler, 'get_container_port', return_value=53245):
            with patch.object(container_handler, 'stop_container'):
                with patch.object(container_handler, 'destroy_container'):
                    response = tsp_stub.AcquireTargetSystem(
                        messages.AcquisitionRequest(
                            user=user,
                            password=password
                        ))

                    tsp_stub.YieldTargetSystem(messages.YieldRequest(id=response.id))

                    container_handler.stop_container.assert_called_once_with(response.id)
                    container_handler.destroy_container.assert_called_once_with(response.id)


@given(id=st.text())
def test_YieldTargetSystem_non_existant_id_gives_not_found(
        tsp_stub: tsp.TargetSystemProviderStub,
        id: str):

    with pytest.raises(grpc.RpcError):
        tsp_stub.YieldTargetSystem(messages.YieldRequest(id=id))

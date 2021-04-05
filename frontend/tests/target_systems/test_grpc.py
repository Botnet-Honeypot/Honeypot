import pytest
from unittest.mock import create_autospec, ANY
from typing import cast
from concurrent import futures
import grpc
import target_system_provider.target_system_provider_pb2_grpc as tsp
import target_system_provider.target_system_provider_pb2 as messages
from frontend.target_systems import create_grpc_target_system_provider, TargetSystemProvider
from frontend.target_systems._grpc import _GrpcTargetSystem, _GrpcTargetSystemProvider


@pytest.fixture
def server_target_system_provider():
    mock = create_autospec(tsp.TargetSystemProviderServicer)

    mock.AcquireTargetSystem.return_value = messages.AcquisitionResult(
        id='6587567',
        address='ADDRESS',
        port=53453)
    mock.YieldTargetSystem.return_value = messages.YieldResult()

    return mock


@pytest.fixture(autouse=True)
def grpc_server(server_target_system_provider: tsp.TargetSystemProviderServicer):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tsp.add_TargetSystemProviderServicer_to_server(server_target_system_provider, server)
    server.add_insecure_port('[::]:50051')
    server.start()

    yield server

    server.stop(grace=None)


@pytest.fixture
def client_target_system_provider():
    provider = create_grpc_target_system_provider('localhost:50051')
    yield provider
    cast(_GrpcTargetSystemProvider, provider).close_channel()


def test_create_grpc_not_None():
    assert not create_grpc_target_system_provider('localhost:50051') is None


def test_acquire_target_system_roundtrip_no_problems(
        client_target_system_provider: TargetSystemProvider,
        server_target_system_provider: tsp.TargetSystemProviderServicer):

    target_system = cast(_GrpcTargetSystem,
                         client_target_system_provider.acquire_target_system(
                             user='Ello',
                             password='LetMeIn'
                         ))

    assert target_system.target_id == '6587567'
    assert target_system.address == 'ADDRESS'
    assert target_system.port == 53453

    server_target_system_provider.AcquireTargetSystem.assert_called_once_with(
        messages.AcquisitionRequest(
            user='Ello',
            password='LetMeIn'
        ),
        ANY
    )


def test_acquire_target_system_UNAVAILABLE_returns_None(
        client_target_system_provider: TargetSystemProvider,
        server_target_system_provider: tsp.TargetSystemProviderServicer):

    def MockAcquireTargetSystem(request, context):
        context.abort(grpc.StatusCode.UNAVAILABLE, '')
        return messages.AcquisitionResult()
    server_target_system_provider.AcquireTargetSystem.side_effect = MockAcquireTargetSystem

    target_system = client_target_system_provider.acquire_target_system(
        user='Ello',
        password='LetMeIn'
    )

    assert target_system is None


def test_yield_target_system_roundtrip_no_problems(
        client_target_system_provider: TargetSystemProvider,
        server_target_system_provider: tsp.TargetSystemProviderServicer):

    # Arrange
    target_system = cast(_GrpcTargetSystem,
                         client_target_system_provider.acquire_target_system(
                             user='Ello',
                             password='LetMeIn'
                         ))
    assert not target_system is None

    # Act
    client_target_system_provider.yield_target_system(target_system)

    # Assert
    server_target_system_provider.YieldTargetSystem.assert_called_once_with(
        messages.YieldRequest(
            id=target_system.target_id
        ),
        ANY
    )

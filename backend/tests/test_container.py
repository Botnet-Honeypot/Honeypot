import pytest
import os
import shutil
import backend.container as container

MAX_CONTAINERS = 5

ID = 1
PORT = 2222
USER = "user"
PASSWORD = "password"
HOSTNAME = "Dell-T140"
UID = 1000
GID = 1000
TIMEZONE = "Europe/London"
SUDO = "true"


@pytest.fixture()
def containerH() -> container.Containers:
    return container.Containers()


@pytest.fixture(autouse=True)
def run_around_tests():
    # Before test

    containerHandler = container.Containers()
    # Change into the correct directory, must be run from /backend/backend/
    os.chdir('..')
    os.chdir("backend")

    # Run test
    yield
    # After test

    # Cleanup, stop and remove containers
    current_path = os.getcwd()

    for i in range(MAX_CONTAINERS):
        try:
            containerHandler.stop_container(i)
            containerHandler.destroy_container(i)
        except:
            continue
    # Remove folders for container storage
    for i in range(MAX_CONTAINERS):
        try:
            shutil.rmtree(os.path.join(current_path, str(i)))
        except:
            continue


def test_create_one_container(containerH: container.Containers):
    containerH.create_container(
        ID, PORT, USER, PASSWORD, HOSTNAME, UID, GID, TIMEZONE, SUDO)
    assert containerH.status_container(1) == container.Status.RUNNING


def test_shared_folder_func(containerH: container.Containers):
    containerH.create_shared_folder(1, USER)
    current_path = os.getcwd()
    assert os.path.isdir(os.path.join(current_path, str(1)))


def test_multiple_shared_folder_func(containerH: container.Containers):
    for i in range(MAX_CONTAINERS):
        containerH.create_shared_folder(i, USER)
    current_path = os.getcwd()
    for i in range(MAX_CONTAINERS):
        assert(os.path.isdir(os.path.join(current_path, str(i))))


def test_stop_container(containerH: container.Containers):
    containerH.create_container(
        ID, PORT, USER, PASSWORD, HOSTNAME, UID, GID, TIMEZONE, SUDO)
    containerH.stop_container(ID)
    assert containerH.status_container(ID) == container.Status.EXITED


def test_destroy_container(containerH: container.Containers):
    containerH.create_container(
        ID, PORT, USER, PASSWORD, HOSTNAME, UID, GID, TIMEZONE, SUDO)
    containerH.stop_container(ID)
    containerH.destroy_container(ID)
    assert containerH.status_container(ID) == container.Status.NOTFOUND


def test_start_multiple_containers(containerH: container.Containers):
    port = 2222
    for i in range(MAX_CONTAINERS):
        containerH.create_container(
            i, port, USER, PASSWORD, HOSTNAME, UID, GID, TIMEZONE, SUDO)
        port += 1
    for i in range(MAX_CONTAINERS):
        assert containerH.status_container(i) == container.Status.RUNNING


def test_start_container_same_port(containerH: container.Containers):
    with pytest.raises(Exception):
        for i in range(MAX_CONTAINERS):
            containerH.create_container(
                i, PORT, USER, PASSWORD, HOSTNAME, UID, GID, TIMEZONE, SUDO)


def test_start_container_same_id(containerH: container.Containers):
    with pytest.raises(Exception):
        for i in range(MAX_CONTAINERS):
            containerH.create_container(
                ID, PORT, USER, PASSWORD, HOSTNAME, UID, GID, TIMEZONE, SUDO)


def test_destroy_twice(containerH: container.Containers):
    with pytest.raises(Exception):
        containerH.create_container(
            ID, PORT, USER, PASSWORD, HOSTNAME, UID, GID, TIMEZONE, SUDO)
        containerH.stop_container(ID)
        containerH.destroy_container(ID)
        containerH.destroy_container(ID)

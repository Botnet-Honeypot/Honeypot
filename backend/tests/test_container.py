import pytest
import os
import shutil
from backend.container import Containers, Status

MAX_CONTAINERS = 5


@pytest.fixture()
def config() -> dict:
    container_handler = Containers()
    container_id = 0
    user = "user"
    password = "password"
    port = 2222

    volumes = {os.getcwd() + "/" + Containers.ID_PREFIX + str(container_id) +
               "/config": {'bind': '/config', 'mode': 'rw'},
               os.getcwd() + "/" + Containers.ID_PREFIX + str(container_id) +
               "/home/": {'bind': '/home/', 'mode': 'rw'}}
    return container_handler.format_config(container_id, port, user, password, volumes)


@pytest.fixture(autouse=True)
def run_around_tests():

    # Before test
    container_handler = Containers()

    # Run test
    yield
    # After test

    # Cleanup, stop and remove containers
    current_path = os.getcwd()

    for i in range(MAX_CONTAINERS):
        try:
            container_id = Containers.ID_PREFIX + str(i)
            container_handler.stop_container(container_id)
            container_handler.destroy_container(container_id)
        except:
            continue
    # Remove folders for container storage
    for i in range(MAX_CONTAINERS):
        try:
            shutil.rmtree(os.path.join(current_path, Containers.ID_PREFIX+str(i)))
        except:
            continue


def test_create_one_container(config: dict):
    container_handler = Containers()
    container_handler.create_container(config)
    assert container_handler.status_container(config["ID"]) == Status.RUNNING


def test_shared_folder_func(config: dict):
    container_handler = Containers()
    container_handler.create_shared_folder(config["ID"], config["User"])
    current_path = os.getcwd()
    assert os.path.isdir(os.path.join(current_path, Containers.ID_PREFIX+str(0)))


def test_multiple_shared_folder_func(config: dict):
    container_handler = Containers()
    for i in range(MAX_CONTAINERS):
        container_handler.create_shared_folder(Containers.ID_PREFIX+str(i), "user")
    current_path = os.getcwd()
    for i in range(MAX_CONTAINERS):
        assert(os.path.isdir(os.path.join(current_path, Containers.ID_PREFIX+str(i))))


def test_stop_container(config: dict):
    container_handler = Containers()
    container_handler.create_container(config)
    container_handler.stop_container(config["ID"])
    assert container_handler.status_container(config["ID"]) == Status.EXITED


def test_destroy_container(config: dict):
    container_handler = Containers()
    container_handler.create_container(config)
    container_handler.stop_container(config["ID"])
    container_handler.destroy_container(config["ID"])
    assert container_handler.status_container(config["ID"]) == Status.NOTFOUND


def test_start_multiple_containers(config: dict):
    container_handler = Containers()
    container_id = 0
    user = "user"
    password = "password"
    port = 2222
    for i in range(MAX_CONTAINERS):
        volumes = {os.getcwd() + "/" + Containers.ID_PREFIX + str(container_id) +
                   "/config": {'bind': '/config', 'mode': 'rw'},
                   os.getcwd() + "/" + Containers.ID_PREFIX + str(container_id) +
                   "/home/": {'bind': '/home/', 'mode': 'rw'}}
        config = container_handler.format_config(container_id, port, user, password, volumes)
        port += 1
        container_id += 1
        container_handler.create_container(config)
    for i in range(MAX_CONTAINERS):
        assert container_handler.status_container(Containers.ID_PREFIX + str(i)) == Status.RUNNING


def test_start_container_same_port(config: dict):
    container_handler = Containers()
    container_id = 0
    user = "user"
    password = "password"
    port = 2222
    with pytest.raises(Exception):
        for i in range(MAX_CONTAINERS):
            volumes = {os.getcwd() + "/" + Containers.ID_PREFIX + str(container_id) +
                       "/config": {'bind': '/config', 'mode': 'rw'},
                       os.getcwd() + "/" + Containers.ID_PREFIX + str(container_id) +
                       "/home/": {'bind': '/home/', 'mode': 'rw'}}
            config = container_handler.format_config(container_id, port, user, password, volumes)
            container_id += 1
            container_handler.create_container(config)


def test_start_container_same_id(config: dict):
    container_handler = Containers()
    container_id = 0
    user = "user"
    password = "password"
    port = 2222
    with pytest.raises(Exception):
        for i in range(MAX_CONTAINERS):
            volumes = {os.getcwd() + "/" + Containers.ID_PREFIX + str(container_id) +
                       "/config": {'bind': '/config', 'mode': 'rw'},
                       os.getcwd() + "/" + Containers.ID_PREFIX + str(container_id) +
                       "/home/": {'bind': '/home/', 'mode': 'rw'}}
            config = container_handler.format_config(container_id, port, user, password, volumes)
            port += 1
            container_handler.create_container(config)


def test_destroy_twice(config: dict):
    container_handler = Containers()
    with pytest.raises(Exception):
        container_handler.create_container(config)
        container_handler.stop_container(config["ID"])
        container_handler.destroy_container(config["ID"])
        container_handler.destroy_container(config["ID"])


def test_format_config():
    container_handler = Containers()
    container_id = 0
    user = "user"
    password = "password"
    port = 2222
    config = container_handler.format_config(container_id, port, user, password, {})
    assert config["User"] == "user"
    assert config["Password"] == "password"
    assert config["Port"] == {'2222/tcp': str(port)}
    assert config["ID"] == Containers.ID_PREFIX + str(container_id)


def test_format_environment():
    container_handler = Containers()
    uid = "1000"
    gid = "1001"
    timezone = "Europe/London"
    user = "user"
    password = "password"
    sudo_access = "true"
    env = container_handler.format_environment(user, password, uid, gid, timezone, sudo_access)
    assert env == ['PUID='+uid, 'PGID='+gid, 'TZ='+timezone, 'SUDO_ACCESS='+sudo_access,
                   'PASSWORD_ACCESS=true', 'USER_PASSWORD='+password, 'USER_NAME='+user]


def test_remove_folder(config: dict):
    container_handler = Containers()
    container_handler.create_shared_folder(config["ID"], config["User"])
    current_path = os.getcwd()
    assert os.path.isdir(os.path.join(current_path, config["ID"]))
    container_handler.remove_folder(config["ID"])
    assert not os.path.isdir(os.path.join(current_path, config["ID"]))

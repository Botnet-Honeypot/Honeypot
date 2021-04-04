import pytest
from backend.container import Containers, Status

MAX_CONTAINERS = 5


@pytest.fixture
def config() -> dict:
    container_id = 0
    user = "user"
    password = "password"
    return Containers.format_config(container_id, user, password)


@pytest.fixture
def container_handler():

    # Before test
    container_handler = Containers()

    # Run test
    yield container_handler
    # After test

    container_handler.shutdown()


def test_create_one_container(config: dict, container_handler: Containers):
    container_handler.create_container(config)
    assert container_handler.status_container(config["ID"]) == Status.RUNNING


def test_stop_container(config: dict, container_handler: Containers):
    container_handler.create_container(config)
    container_handler.stop_container(config["ID"])
    assert container_handler.status_container(config["ID"]) == Status.EXITED


def test_destroy_container(config: dict, container_handler: Containers):
    container_handler.create_container(config)
    container_handler.stop_container(config["ID"])
    container_handler.destroy_container(config["ID"])
    assert container_handler.status_container(config["ID"]) == Status.NOTFOUND


def test_start_multiple_containers(config: dict, container_handler: Containers):
    user = "user"
    password = "password"
    for i in range(MAX_CONTAINERS):
        config = Containers.format_config(i, user, password)
        container_handler.create_container(config)
    for i in range(MAX_CONTAINERS):
        assert container_handler.status_container(Containers.ID_PREFIX + str(i)) == Status.RUNNING


def test_start_container_same_port(config: dict, container_handler: Containers):
    user = "user"
    password = "password"
    with pytest.raises(Exception):
        for i in range(2):
            config = Containers.format_config(i, user, password, port=5555)
            container_handler.create_container(config)


def test_start_container_same_id(config: dict, container_handler: Containers):
    container_id = 0
    user = "user"
    password = "password"
    with pytest.raises(Exception):
        for i in range(MAX_CONTAINERS):
            config = Containers.format_config(container_id, user, password)
            container_handler.create_container(config)


def test_destroy_twice(config: dict, container_handler: Containers):
    with pytest.raises(Exception):
        container_handler.create_container(config)
        container_handler.stop_container(config["ID"])
        container_handler.destroy_container(config["ID"])
        container_handler.destroy_container(config["ID"])


def test_format_config():
    container_id = 0
    user = "user"
    password = "password"
    config = Containers.format_config(container_id, user, password, {})
    assert config["User"] == "user"
    assert config["Password"] == "password"
    assert config["ID"] == Containers.ID_PREFIX + str(container_id)


def test_format_environment():
    uid = "1000"
    gid = "1001"
    timezone = "Europe/London"
    user = "user"
    password = "password"
    sudo_access = "true"
    env = Containers._format_environment(user, password, uid, gid, timezone, sudo_access)
    assert env == ['PUID='+uid, 'PGID='+gid, 'TZ='+timezone, 'SUDO_ACCESS='+sudo_access,
                   'PASSWORD_ACCESS=true', 'USER_PASSWORD='+password, 'USER_NAME='+user]


def test_prune_volumes(config: dict, container_handler: Containers):
    container_handler.create_container(config)
    container_handler.stop_container(config["ID"])
    container_handler.destroy_container(config["ID"])
    container_handler.prune_volumes()
    with pytest.raises(Exception):
        container_handler.get_volume(config["ID"])


def test_get_volume(config: dict, container_handler: Containers):
    container_handler.create_container(config)
    assert str(container_handler.get_volume(config["ID"] + "config")) == "<Volume: openssh-se>"


def test_get_port(config: dict, container_handler: Containers):
    config['Port'] = {'2222/tcp': 2222}
    container_handler.create_container(config)
    assert container_handler.get_container_port(config["ID"]) == 2222

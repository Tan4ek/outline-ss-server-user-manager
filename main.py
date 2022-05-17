import logging
import os
import subprocess
from dataclasses import dataclass
from subprocess import TimeoutExpired
from typing import List, Optional

import yaml
from fastapi import FastAPI, Response, status
from filelock import FileLock
from pydantic import BaseModel
from yaml import Loader

logging.basicConfig(level='INFO',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SSPORT = int(os.environ.get('SS_USER_PORT', 9000))
CONFIG_FILE_PATH = os.environ.get('SS_CONFIG_PATH', 'outline-ss-server/config.yml')
CIPHER = os.environ.get('SS_CIPHER', 'chacha20-ietf-poly1305')

if CIPHER not in {'chacha20-ietf-poly1305', 'aes-256-gcm', 'aes-192-gcm', 'aes-128-gcm'}:
    logger.error(f"Not valid SS_CIPHER: {CIPHER}. "
                 f"Valid values: ['chacha20-ietf-poly1305', 'aes-256-gcm', 'aes-192-gcm', 'aes-128-gcm']")
    import sys
    sys.exit(1)

CONFIG_FILE_PATH_LOCK = CONFIG_FILE_PATH + '.lock'

logger.info(f"SSPORT: {SSPORT}, CONFIG_FILE_PATH: {CONFIG_FILE_PATH}, CIPHER: {CIPHER}")


@dataclass
class UserConfig:
    id: str
    port: int
    cipher: str
    secret: str


@dataclass
class State:
    ssport: int
    cipher: str
    users: List[UserConfig]


def get_state() -> State:
    with open(CONFIG_FILE_PATH, 'r') as f:
        yaml_structure = yaml.load(f, Loader)
        users = [
            UserConfig(
                id=u['id'],
                port=u['port'],
                cipher=u['cipher'],
                secret=u['secret']
            )
            for u in (yaml_structure.get('keys') if yaml_structure.get('keys') else [])
        ]
        return State(
            ssport=SSPORT,
            cipher=CIPHER,
            users=users
        )


def save_state(state: State):
    with open(CONFIG_FILE_PATH, 'w') as f:
        serialized_users = [
            {
                'cipher': u.cipher,
                'id': u.id,
                'port': u.port,
                'secret': u.secret
            }
            for u in state.users
        ]
        yaml.dump({'keys': serialized_users}, f)


def find_user(state: State, user_id: str) -> Optional[UserConfig]:
    result = [x for x in state.users if x.id == user_id]
    if result:
        return result[0]
    return None


def restart_outline_ss_server():
    process = subprocess.Popen(['supervisorctl', 'restart', 'ss-server'],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               universal_newlines=True)
    try:
        process.communicate(timeout=10)
        logger.info("Success restart 'ss-server'.")
    except TimeoutExpired as e:
        process.kill()
        logger.error(
            f"Restart ss server timeout after 10 seconds. \n stdout: {process.stdout}, stderr: {process.stderr}", e)
        raise e


app = FastAPI()
config_file_lock = FileLock(CONFIG_FILE_PATH_LOCK, timeout=5)


class User(BaseModel):
    user_id: str
    sssecret: str


@config_file_lock
@app.post("/user", status_code=200)
def create_user(user: User, response: Response):
    state = get_state()
    if user.user_id in {x.id for x in state.users}:
        response.status_code = status.HTTP_409_CONFLICT
        return {}
    config_user = UserConfig(
        id=user.user_id,
        port=state.ssport,
        cipher=state.cipher,
        secret=user.sssecret
    )
    new_users = state.users.copy()
    new_users.append(config_user)
    new_state = State(ssport=state.ssport, cipher=state.cipher, users=new_users)
    save_state(new_state)

    restart_outline_ss_server()
    logger.info(f"Create new user {config_user.id}")
    return {
        'user_id': config_user.id,
        'port': config_user.port,
        'cipher': config_user.cipher,
        'secret': config_user.secret
    }


@app.get("/user/{user_id}", status_code=200)
def get_user(user_id: str, response: Response):
    state = get_state()
    user = find_user(state, user_id)
    if not user:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    return {
        'user_id': user.id,
        'port': user.port,
        'cipher': user.cipher,
        'secret': user.secret
    }


@config_file_lock
@app.delete('/user/{user_id}', status_code=204)
def delete_user(user_id: str, response: Response):
    state = get_state()
    user = find_user(state, user_id)
    if not user:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}

    filtered_users = [x for x in state.users if x.id != user_id]
    new_state = State(ssport=state.ssport, cipher=state.cipher, users=filtered_users)
    save_state(new_state)

    restart_outline_ss_server()

    logger.info(f"Delete user {user_id}")
    return {}


@app.get('/users', status_code=200)
def get_users():
    state = get_state()
    users = state.users
    return [{'user_id': x.id} for x in users]


@config_file_lock
@app.post('/restart-ss-server')
def restart_ss_server():
    restart_outline_ss_server()
    return {}


if __name__ == '__main__':
    s = get_state()

    save_state(s)

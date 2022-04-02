import subprocess
from dataclasses import dataclass
from typing import List, Optional

import yaml
from fastapi import FastAPI, Response, status
from filelock import FileLock
from pydantic import BaseModel
from yaml import Loader

# TODO: get from config or env or args
SSPORT = 9000
CONFIG_FILE_PATH = 'outline-ss-server/config.yml'
CONFIG_FILE_PATH_LOCK = CONFIG_FILE_PATH + '.lock'
CIPHER = 'chacha20-ietf-poly1305'


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
            for u in yaml_structure.get('keys', [])
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
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    print(stdout)
    print(stderr)


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
    user = UserConfig(
        id=user.user_id,
        port=state.ssport,
        cipher=state.cipher,
        secret=user.sssecret
    )
    new_users = state.users.copy()
    new_users.append(user)
    new_state = State(ssport=state.ssport, cipher=state.cipher, users=new_users)
    save_state(new_state)

    restart_outline_ss_server()
    return {
        'port': user.port,
        'cipher': user.cipher,
        'secret': user.secret
    }


@app.get("/user/{user_id}", status_code=200)
def get_user(user_id: str, response: Response):
    state = get_state()
    user = find_user(state, user_id)
    if not user:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {}
    return {
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
    print(s)

    pass

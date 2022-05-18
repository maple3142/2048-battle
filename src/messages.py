from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Tuple, List, Any
from enum import IntEnum
import json

class Direction(IntEnum):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

@dataclass_json
@dataclass
class ErrorMessage:
    message: str


@dataclass_json
@dataclass
class NewRoomRequest:
    pass


@dataclass_json
@dataclass
class NewRoomResponse:
    room_id: str


@dataclass_json
@dataclass
class ConnectRequest:
    room_id: str


@dataclass_json
@dataclass
class ConnectedMessage:
    pass


@dataclass_json
@dataclass
class DisconnectedMessage:
    pass


@dataclass_json
@dataclass
class ClientUpdateMessage:
    score: int
    new_blocks: List[int]
    board: List[List[int]]
    move_direction: Direction


@dataclass_json
@dataclass
class OpponentUpdateMessage:
    score: int
    penalty_blocks: List[int]
    board: List[List[int]]
    move_direction: Direction


@dataclass_json
@dataclass
class ClientWinMessage:
    score: int


@dataclass_json
@dataclass
class OpponentWinMessage:
    score: int


type_to_class = {
    "error": ErrorMessage,
    "new_room": NewRoomRequest,
    "new_room_id": NewRoomResponse,
    "connect": ConnectRequest,
    "connected": ConnectedMessage,
    "disconnected": DisconnectedMessage,
    "client_update": ClientUpdateMessage,
    "opponent_update": OpponentUpdateMessage,
    "client_win": ClientWinMessage,
    "opponent_win": OpponentWinMessage,
}
class_to_type = {v: k for k, v in type_to_class.items()}


def deserialize(msg: str) -> Tuple[str, Any]:
    x = json.loads(msg)
    return x["type"], type_to_class[x["type"]].from_dict(x["data"])


def serialize(data: Any) -> str:
    return json.dumps({"type": class_to_type[data.__class__], "data": data.to_dict()})

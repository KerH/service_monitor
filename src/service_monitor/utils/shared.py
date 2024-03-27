"""Represent shared information between client and server."""

from enum import Enum, auto


PROXY_SUB_PORT = 4998
PROXY_PUB_PORT = 4999


class ServerStatusCode(Enum):
    """Server status codes - used as a feedback to the client."""

    SUCCESS = auto()
    INVALID_HEADER = auto()
    FAILURE = auto()


class Headers(Enum):
    """Headers for messages from client to server."""

    REGISTER_CLIENT = auto()
    REGISTER_SERVICE = auto()
    SET_OUTAGE_TIME = auto()
    SET_GRACE_TIME = auto()

"""Proxy module - connect many subscribers to many publishers."""

import zmq


class ForwarderDeviceException(Exception):
    pass


class ForwarderDevice:
    """Forwarder Device to connect between publishers and subscribers."""

    def __init__(self, frontend_port: int, backend_port: int) -> None:
        """Initialize a new device.

        Args:
            frontend_port(int): listen to publishers
            backend_port(int): speaks to subscribers
        """
        self._frontend_port = frontend_port
        self._backend_port = backend_port
        self._ctx = zmq.Context(1)
        # frontend for publishers
        self._frontend = self._ctx.socket(zmq.SUB)
        # subscribe on all topics
        self._frontend.setsockopt_string(zmq.SUBSCRIBE, "")
        # backend for subscribers
        self._backend = self._ctx.socket(zmq.PUB)

    @property
    def frontend_port(self):
        return self._frontend_port

    @property
    def backend_port(self):
        return self._backend_port

    def run(self) -> None:
        """Run Forwarder Device.

        Raise:
            ForwarderDeviceException: in case of failure of creating the device
        """
        try:
            self._frontend.bind(f"tcp://*:{self._frontend_port}")
            self._backend.bind(f"tcp://*:{self._backend_port}")
            # register forwarder device
            zmq.device(zmq.FORWARDER, self._frontend, self._backend)

        except Exception as err:
            raise ForwarderDeviceException(err)

        finally:
            self._frontend.close()
            self._backend.close()
            self._ctx.term()

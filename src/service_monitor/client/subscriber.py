"""Client subscriber module for services updates."""

import logging

import zmq


class SubscriberException(Exception):
    pass


class Subscriber:
    """Represent a client subscriber."""

    RECV_TIMEOUT = 5000  # 5 seconds

    def __init__(
        self,
        ctx: zmq.Context,
        server_ip: str,
        subscribers_port: int,
        topic: str,
    ) -> None:
        """Initialize a new client subscriber.

        Args:
            ctx(zmq.Context): thread-safe context from client
            server_ip(str): server IP
            subscribers_port(int): backend port for subscribers in proxy
            topic(str): the topic to subscribe on

        Raise:
            SubscriberException: in case subscriber is not able to connect
        """
        try:
            self._socket = ctx.socket(zmq.SUB)
            self._socket.setsockopt(zmq.RCVTIMEO, Subscriber.RECV_TIMEOUT)
            self._socket.setsockopt(zmq.SUBSCRIBE, topic.encode())
            self._socket.connect(f"tcp://{server_ip}:{subscribers_port}")
            self._terminate = False

        except zmq.ZMQError as err:
            raise SubscriberException(err)

    @property
    def terminate(self):
        return self._terminate

    @terminate.setter
    def terminate(self, val):
        self._terminate = val

    def run(self):
        """Main subscriber function for services updates."""
        while True:
            try:
                client_id, service, service_status = [
                    var.decode() for var in self._socket.recv_multipart()
                ]
                logging.info(
                    f"Client {client_id}, service {service} "
                    f"status:{service_status}"
                )

            except zmq.ZMQError:
                if self._terminate:
                    self.cleanup()
                    break

    def cleanup(self):
        """Release subscriber resources."""
        self._socket.close()

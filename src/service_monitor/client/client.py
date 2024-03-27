import logging
import threading
from datetime import datetime

import zmq
from munch import Munch

from src.service_monitor.client.subscriber import (
    Subscriber,
    SubscriberException,
)
from src.service_monitor.utils.shared import (
    Headers,
    ServerStatusCode,
    PROXY_PUB_PORT,
)


class ClientConnectionException(Exception):
    pass


class ClientSubscriberException(Exception):
    pass


class ClientServiceRegistrationException(Exception):
    pass


class ClientSetOutageTimeException(Exception):
    pass


class ClientSetGraceTimeException(Exception):
    pass


class Client:
    """Represent a client.

    Allows the following:
        * Register a service to monitor on
        * Set outage time for a specific service
        * Set grace time for all client's services
    """

    def __init__(self, server_ip: str, server_port: int) -> None:
        """Initialize a new client.

        Args:
            server_ip(str): server IP
            server_port(int): server port

        Raise:
            ClientConnectionException: in case of failure to connect server
            ClientSubscriberException: in case of failure to create subscriber
        """
        self._server_ip = server_ip
        self._server_port = server_port
        self._ctx = zmq.Context.instance()
        self._cmd_socket = self._ctx.socket(zmq.REQ)
        try:
            self._id = self._connect_and_get_id()
            self._set_logging()
            self._subscriber = Subscriber(
                ctx=self._ctx,
                server_ip=server_ip,
                subscribers_port=PROXY_PUB_PORT,
                topic=self._id,
            )
            self._subscriber_t = threading.Thread(target=self._subscriber.run)
            self._subscriber_t.start()

        except SubscriberException as err:
            raise ClientSubscriberException(err)

    @property
    def id(self):
        return self._id

    def _set_logging(self):
        """Configure logging for client."""
        logging.basicConfig(
            filename=f"monitor_client_{self._id}.log",
            level=logging.INFO,
            format="{asctime} - {levelname} - {message}",
            style="{",
        )

    def _connect_and_get_id(self):
        """Connect to monitor server and obtain ID.

        Raise:
            ClientConnectionException: in case of registration failure
        """
        try:
            self._cmd_socket.connect(
                f"tcp://{self._server_ip}:{self._server_port}"
            )
            self._cmd_socket.send_json(
                Munch(header=Headers.REGISTER_CLIENT.name)
            )
            server_response = Munch(self._cmd_socket.recv_json())
            if server_response.header != ServerStatusCode.SUCCESS.name:
                raise ClientConnectionException("Could not register client")

            return server_response.client_id

        except (AttributeError, zmq.error.ZMQError) as err:
            raise ClientConnectionException(err)

    def register_service(
        self, service_host: str, service_port: int, poll_freq: int
    ):
        """Register service to monitor on.

        Args:
            service_host(str): IP address of service
            service_port(int): service port
            poll_freq(int): how frequent to poll the service [in seconds]

        Raise:
            ClientServiceRegistrationException:
                in case of failure to register service
        """
        msg = Munch(
            header=Headers.REGISTER_SERVICE.name,
            service_host=service_host,
            service_port=service_port,
            poll_freq=poll_freq,
            client_id=self._id,
        )

        # send server a request to register service
        self._cmd_socket.send_json(msg)
        server_response = Munch(self._cmd_socket.recv_json())
        if server_response.header != ServerStatusCode.SUCCESS.name:
            logging.error(
                f"Service {(service_host, service_port)} registration "
                f"failed with the following error:\n{server_response.err}"
            )
            raise ClientServiceRegistrationException(server_response.err)

    def register_service_outage(
        self,
        service_host: str,
        service_port: int,
        start_time: datetime,
        end_time: datetime,
    ):
        """Register service outage time.

        Args:
            service_host(str): IP address of service
            service_port(int): service port
            start_time(datetime): outage start time
            end_time(datetime): outage end time

        Raise:
            ClientSetOutageTimeException:
                in case of failure to register service outage time
        """
        msg = Munch(
            header=Headers.SET_OUTAGE_TIME.name,
            service_host=service_host,
            service_port=service_port,
            start_time=start_time,
            end_time=end_time,
            client_id=self._id,
        )

        # send server a request to set outage time
        self._cmd_socket.send_json(msg)
        server_response = Munch(self._cmd_socket.recv_json())
        if server_response.header != ServerStatusCode.SUCCESS.name:
            logging.error(
                "Failed to set outage time for service: "
                f"{(service_host, service_port)}. "
                f"The following error occurred:\n{server_response.err}"
            )
            raise ClientSetOutageTimeException(server_response.err)

    def register_grace_time(self, grace_time: int):
        """Register grace time for all client's services.

        Args:
            grace_time(int): the amount of time in seconds
                             -1 to cancel grace time

        Raise:
            ClientSetGraceTimeException:
                in case of failure to set grace time
        """
        msg = Munch(
            header=Headers.SET_GRACE_TIME.name,
            grace_time=grace_time,
            client_id=self._id,
        )

        # send server a request to set grace time to all services
        self._cmd_socket.send_json(msg)
        server_response = Munch(self._cmd_socket.recv_json())
        if server_response.header != ServerStatusCode.SUCCESS.name:
            logging.error(
                f"Failed to set grace time: {grace_time} for "
                "client's services. "
                f"The following error occurred:\n{server_response.err}"
            )
            raise ClientSetGraceTimeException(server_response.err)

    def cleanup(self):
        """Cleanup client object."""
        self._subscriber.terminate = True
        self._subscriber_t.join()
        self._cmd_socket.close()
        self._ctx.term()

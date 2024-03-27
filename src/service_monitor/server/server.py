"""Module for running a monitor server."""

import sys
import time
import click
import queue
import logging
import threading

import zmq
from munch import Munch

from src.service_monitor.server.publisher import ServiceStatusPublisher
from src.service_monitor.server.proxy import (
    ForwarderDevice,
    ForwarderDeviceException,
)
from src.service_monitor.utils.shared import (
    Headers,
    ServerStatusCode,
    PROXY_SUB_PORT,
    PROXY_PUB_PORT,
)


class MontiorServerException(Exception):
    pass


class MonitorServer:
    """Monitor server.

    Responsible to monitor over network services and notify clients.
    """

    DEFAULT_PORT = 5000

    def __init__(
        self, port: int = DEFAULT_PORT, log_file_path: str = "."
    ) -> None:
        """Initialize a new server.

        Args:
            port(int): the port to bind the server to
        Raise:
            MontiorServerException: in case of failure to start the server
                                    properly. Including proxy initialization
        """
        logging.basicConfig(
            filename=f"{log_file_path}/monitor_server.log",
            level=logging.INFO,
            format="{asctime} - {levelname} - {message}",
            style="{",
        )
        self._port = port
        self._ctx = zmq.Context()
        self._rep_socket = self._ctx.socket(zmq.REP)
        self._service_to_publisher = dict()
        self._service_to_service_queue = dict()
        self._client_to_services = dict()
        self._handlers = {
            Headers.REGISTER_CLIENT.name: self._register_client,
            Headers.REGISTER_SERVICE.name: self._register_service,
            Headers.SET_OUTAGE_TIME.name: self._register_service_outage,
            Headers.SET_GRACE_TIME.name: self._update_grace_time,
        }

        try:
            # create proxy for pub/sub
            proxy = ForwarderDevice(
                frontend_port=PROXY_SUB_PORT, backend_port=PROXY_PUB_PORT
            )
            threading.Thread(target=proxy.run, daemon=True).start()
        except ForwarderDeviceException as err:
            raise MontiorServerException(err)

    def _register_client(self, msg: Munch):
        """Register a new client to the server.

        Args:
            msg(Munch): the message received from client

        Return:
            Munch - Response to the client with SUCCESS status code and id
        """
        new_client_id = str(time.time())
        self._client_to_services[new_client_id] = list()

        logging.info(f"Registered a new client with client id: {new_client_id}")
        return Munch(
            header=ServerStatusCode.SUCCESS.name, client_id=new_client_id
        )

    def _register_service(self, msg: Munch):
        """Register service to the services being monitored.

        Args:
            msg(Munch): the message received from client

        Return:
            Munch - Response to the client with SUCCESS or FAILURE status
                    SUCCESS in case service was registered successfully
                    FAILURE otherwise
        """
        service = (msg.service_host, msg.service_port)
        if service not in self._service_to_publisher:
            try:
                self._service_to_service_queue[service] = queue.Queue()
                self._service_to_publisher[service] = ServiceStatusPublisher(
                    ctx=self._ctx,
                    host=msg.service_host,
                    port=int(msg.service_port),
                    pub_port=PROXY_SUB_PORT,
                    service_requests=self._service_to_service_queue[service],
                )

            except zmq.error.ZMQError as err:
                return Munch(header=ServerStatusCode.FAILURE.name, err=err)

        service_publisher = self._service_to_publisher.get(service)
        poll_thread = threading.Timer(
            int(msg.poll_freq),
            service_publisher.poll,
            args=(msg.client_id, int(msg.poll_freq)),
        )
        poll_thread.daemon = True
        poll_thread.start()

        logging.info(
            f"Start to monitor over service: {service} for "
            f"client: {msg.client_id}"
        )
        return Munch(header=ServerStatusCode.SUCCESS.name)

    def _register_service_outage(self, msg: Munch):
        """Register outage time for a specific service, for given client.

        Args:
            msg (Munch): the message received from client

        Return:
            Munch - Response to the client with SUCCESS or FAILURE status
                    SUCCESS in case service is currently monitored
                    FAILURE otherwise
        """
        service = (msg.service_host, msg.service_port)
        if service not in self._service_to_publisher:
            err_msg = f"Received {msg.header} request over not monitored "
            f"service {service}"
            logging.error(err_msg)
            return Munch(header=ServerStatusCode.FAILURE.name, err=err_msg)

        # update publisher with outage time for given client
        self._service_to_service_queue[service].put(
            (msg.start_time, msg.end_time, msg.client_id)
        )

        logging.info(
            f"Set outage time for service: {service} as requested "
            f"from client {msg.client_id}"
        )
        return Munch(header=ServerStatusCode.SUCCESS.name)

    def _update_grace_time(self, msg: Munch):
        """Update grace time for all client's services.

        Args:
            msg (Munch): the message received from client

        Return:
            Munch - Response to the client with SUCCESS or FAILURE status
                    SUCCESS in case grace time was set successfully
                    FAILURE otherwise
        """
        if msg.client_id not in self._client_to_services:
            return Munch(
                header=ServerStatusCode.FAILURE.name,
                err=f"Client {msg.client_id} is not registered.",
            )

        for service in self._client_to_services[msg.client_id]:
            self._service_to_publisher[service].queue.put(
                (msg.client_id, msg.grace_time)
            )

        logging.info(
            f"Set outage time for service: {service} as requested "
            f"from client {msg.client_id}"
        )
        return Munch(header=ServerStatusCode.SUCCESS.name)

    def _invalid_msg(self, msg: Munch):
        """Handle invalid message from client.

        Log the error and return INVALID_HEADER status code to client.

        Args:
            msg(Munch): the message received from client

        Return:
            Munch - Response to the client with INVALID HEADER status
        """
        logging.error(f"Received invalid command: {msg.header}")
        return Munch(header=ServerStatusCode.INVALID_HEADER.name)

    def run(self) -> None:
        """Receive commands from clients and handle them."""
        self._rep_socket.bind(f"tcp://*:{self._port}")
        try:
            while True:
                msg = Munch(self._rep_socket.recv_json())
                # handle message
                handler_res = self._handlers.get(
                    msg.get("header"), lambda: self._invalid_msg
                )(msg)

                # send relevant information to client
                self._rep_socket.send_json(handler_res)

        except (zmq.ZMQError, TypeError) as err:
            logging.error(err)
            self.cleanup()

    def cleanup(self) -> None:
        logging.info("Server is shutting down...")
        self._rep_socket.close()
        self._ctx.term()


@click.command(help="Run server")
@click.option("--port", "-p", required=True, type=int, help="server port")
@click.option(
    "--log-file-path", default=".", type=str, help="path for log file"
)
def run(port: int, log_file_path: str):
    try:
        server = MonitorServer(port=port, log_file_path=log_file_path)
        server.run()
    except KeyboardInterrupt:
        server.cleanup()
        sys.exit(0)


if __name__ == "__main__":
    run()

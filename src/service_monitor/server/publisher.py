"""Montior over service and publish its status."""

import json
import queue
import socket
import threading
from typing import Tuple
from time import sleep, time
from datetime import datetime
from collections import defaultdict

import zmq
from munch import Munch


class ServiceStatusPublisher:
    """Publisher for updating service status."""

    MIN_POLL_FREQ = 1  # seconds
    last_poll = None
    min_poll_time_lock = threading.Lock()
    pub_socket_lock = threading.Lock()
    client_outage_requests_lock = threading.Lock()
    clients_gt_request_lock = threading.Lock()

    # service possible status
    SERVICE_UP = "UP"
    SERVICE_DOWN = "DOWN"

    # outage request format
    OUTAGE_REQUEST_FIELDS = Munch(
        start_time_idx=0, end_time_idx=1, client_id_idx=2
    )

    # grace time request format
    GRACE_TIME_REQUEST_FIELDS = Munch(grace_time_idx=0, client_id_idx=1)

    def __init__(
        self,
        ctx: zmq.Context,
        host: str,
        port: int,
        pub_port: int,
        service_requests: queue.Queue,
    ) -> None:
        """Initialize new publisher.

        Args:
            ctx(zmq.Context): thread-safe context from server
            host(str): service IP
            port(str): service port
            pub_port(int): proxy port for publisher
            service_requests(queue.Queue): queue for receiving requests
        """
        self._service = Munch(host=host, port=port)
        self._pub_socket = ctx.socket(zmq.PUB)
        self._pub_socket.connect(f"tcp://localhost:{pub_port}")
        self._service_requests = service_requests
        self._client_outage_requests = defaultdict(list)
        self._clients_gt_request = defaultdict(list)

    @property
    def service(self):
        return self._service

    @property
    def service_requests(self):
        return self._service_requests

    def _wait_min_poll_freq(self) -> None:
        """Wait at least minimum polling frequency."""
        if not ServiceStatusPublisher.last_poll:
            return
        while (
            int(time() - ServiceStatusPublisher.last_poll)
            <= ServiceStatusPublisher.MIN_POLL_FREQ
        ):
            pass

    def _update_gt_request(self, request: Tuple) -> None:
        """Update monitor grace time on service for relevant client.

        Args:
            request(Tuple): (client_id, grace_time) format
        """
        with ServiceStatusPublisher.clients_gt_request_lock:
            self._clients_gt_request[
                request[
                    ServiceStatusPublisher.GRACE_TIME_REQUEST_FIELDS.client_id_idx
                ]
            ] = request[
                ServiceStatusPublisher.GRACE_TIME_REQUEST_FIELDS.grace_time_idx
            ]

    def _update_outage_request(self, request: Tuple) -> None:
        """Update service outage time for client.

        Args:
            request(Tuple): (start_time, end_time, client_id) format
        """
        with ServiceStatusPublisher.client_outage_requests_lock:
            self._client_outage_requests[
                request[
                    ServiceStatusPublisher.OUTAGE_REQUEST_FIELDS.client_id_idx
                ]
            ].append(
                request[
                    : ServiceStatusPublisher.OUTAGE_REQUEST_FIELDS.client_id_idx
                ]
            )

    def _update_requests(self) -> None:
        """Update requests from clients."""
        if not self._service_requests.empty():
            request = self._service_requests.get_nowait()
            # handle grace time request
            if len(request) == len(
                ServiceStatusPublisher.GRACE_TIME_REQUEST_FIELDS
            ):
                self._update_gt_request(request)
            # handle service outage request
            elif len(request) == len(
                ServiceStatusPublisher.OUTAGE_REQUEST_FIELDS
            ):
                self._update_outage_request(request)

    def _is_in_outage_time(self, client_id: str) -> bool:
        """Determine if the service is in an outage time for given client.

        Args:
            client_id(str): client id

        Return:
            bool: True in case the service is in an outage time
                  False otherwise
        """
        for start_time, end_time in self._client_outage_requests[client_id]:
            if start_time <= datetime.now() <= end_time:
                return True

        return False

    def poll(self, client_id: str, poll_freq: int) -> None:
        """Monitor service by trying to establish a tcp connection.

        Args:
            client_id(str): client id
            poll_freq(int): polling frequency in seconds
        """
        try:
            while True:
                # handle requests (outage, grace time) for service
                self._update_requests()
                # avoid monitoring during outage time for requesting client
                if self._is_in_outage_time(client_id):
                    continue
                # monitor service
                service_socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM
                )
                service_status = None
                with ServiceStatusPublisher.min_poll_time_lock:
                    self._wait_min_poll_freq()
                    ServiceStatusPublisher.last_poll = time()
                    try:
                        service_socket.connect(
                            (self._service.host, self._service.port)
                        )
                        service_status = ServiceStatusPublisher.SERVICE_UP

                    except ConnectionRefusedError:
                        service_status = ServiceStatusPublisher.SERVICE_DOWN

                    finally:
                        service_socket.close()

                with ServiceStatusPublisher.pub_socket_lock:
                    self._pub_socket.send_multipart(
                        [
                            client_id.encode(),
                            json.dumps(self._service).encode(),
                            service_status.encode(),
                        ]
                    )

                sleep(poll_freq)

        finally:
            self._pub_socket.close()

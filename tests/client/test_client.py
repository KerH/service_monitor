"""Test integration between client and server."""

import pytest

import threading

from src.service_monitor.server.server import MonitorServer
from src.service_monitor.client.client import Client


@pytest.mark.skip(reason="Integration tests not fully implemented.")
class TestClient:

    SERVER_IP = "localhost"
    SERVER_PORT = 5000

    def setup_method(self):
        """Initialize new client for tests."""
        # initialize server
        self._server = MonitorServer()
        self._server_t = threading.Thread(target=self._server.run)
        self._server_t.start()

        # initialize client
        self._client = Client(
            server_ip=TestClient.SERVER_IP, server_port=TestClient.SERVER_PORT
        )

    def teardown_method(self):
        """Release server and client resources."""
        # release server
        self._server.cleanup()
        self._server_t.join()

        # release client
        self._client.cleanup()

    @pytest.mark.skip(reason="Not implemented")
    def test_id(self):
        pass

    @pytest.mark.skip(reason="Not implemented")
    def test_register_service(self):
        pass

    @pytest.mark.skip(reason="Not implemented")
    def test_register_service_outage(self):
        pass

    @pytest.mark.skip(reason="Not implemented")
    def test_register_grace_time(self):
        pass

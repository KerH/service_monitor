"""Test ServiceStatusPublisher class."""

import zmq
import queue
import pytest
from typing import Tuple

from munch import Munch

from src.service_monitor.server.publisher import ServiceStatusPublisher


@pytest.fixture(scope="class")
def service():
    return Munch(host="localhost", port=5000)


@pytest.fixture(scope="class")
def service_requests():
    return queue.Queue()


@pytest.mark.usefixtures("service", "service_requests")
class TestServiceStatusPublisher:
    """Test publisher functionality."""

    @classmethod
    def setup_class(cls):
        """Create publisher to test."""
        cls.publisher = ServiceStatusPublisher(
            ctx=zmq.Context(),
            host="localhost",
            port=5000,
            pub_port=4998,
            service_requests=queue.Queue(),
        )

    def test_service(self, service: Tuple):
        """Test retrieval of service property."""
        assert self.publisher.service == service

    def test_service_requests(self, service_requests: queue.Queue):
        """Test retrieval of service_requests queue property."""
        assert (
            self.publisher.service_requests.qsize() == service_requests.qsize()
        )

    @pytest.mark.skip(reason="Not implemented")
    def test_poll(self):
        pass

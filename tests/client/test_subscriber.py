"""Test Subscriber class."""

import zmq
import pytest

from src.service_monitor.client.subscriber import Subscriber


@pytest.fixture(scope="class")
def terminate_true():
    return True


@pytest.fixture(scope="class")
def terminate_false():
    return False


@pytest.mark.usefixtures("terminate_true", "terminate_false")
class TestSubscriber:
    """Test subscriber functionality."""

    def setup_method(self):
        """Create Subscriber to test."""
        self._subscriber = Subscriber(
            ctx=zmq.Context(),
            server_ip="localhost",
            subscribers_port=4999,
            topic="123.456",
        )

    def teardown_method(self):
        """Cleanup subscriber resources."""
        self._subscriber.cleanup()

    def test_terminate(self):
        """Test working with terminate property."""
        assert not self._subscriber.terminate
        self._subscriber.terminate = True
        assert self._subscriber.terminate

    @pytest.mark.skip(reason="Not implemented")
    def test_run(self):
        pass

"""Test ForwarderDevice module."""

import pytest

from src.service_monitor.server.proxy import ForwarderDevice


class TestForwarderDevice:
    """Test ForwarderDevice functionality."""

    FRONTEND_PORT = 4998
    BACKEND_PORT = 4999

    @classmethod
    def setup_class(cls):
        """Create forwarder device to test."""
        cls.forwarder_device = ForwarderDevice(
            frontend_port=cls.FRONTEND_PORT, backend_port=cls.BACKEND_PORT
        )

    @pytest.mark.parametrize("frontend_port", [4998])
    def test_frontend_port(self, frontend_port: int):
        """Test retrieval of frontend port from device."""
        assert self.forwarder_device.frontend_port == frontend_port

    @pytest.mark.parametrize("backend_port", [4999])
    def test_backend_port(self, backend_port: int):
        """Test retrieval of backend port from device."""
        assert self.forwarder_device.backend_port == backend_port

    @pytest.mark.skip(reason="Not implemented")
    def test_run(self):
        pass

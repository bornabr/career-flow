"""Pytest configuration and shared fixtures."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    from app.main import app
    return TestClient(app)

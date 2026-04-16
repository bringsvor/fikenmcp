import pytest
import respx

from fiken_mcp.config import Settings
from fiken_mcp.client import FikenClient

BASE = "https://api.fiken.no/api/v2"
SLUG = "test-company"


@pytest.fixture
def settings():
    return Settings(api_token="test-token", company_slug=SLUG, base_url=BASE)


@pytest.fixture
async def client(settings):
    c = FikenClient(settings)
    yield c
    await c.aclose()


@pytest.fixture
def mock_api():
    with respx.mock(base_url=BASE, assert_all_called=False) as api:
        yield api

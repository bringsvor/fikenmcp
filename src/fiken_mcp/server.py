from mcp.server.fastmcp import FastMCP

from .client import FikenClient
from .tools.company import fiken_company_get

mcp = FastMCP("fiken")
_client: FikenClient | None = None


def _get_client() -> FikenClient:
    global _client
    if _client is None:
        _client = FikenClient()
    return _client


@mcp.tool()
async def fiken_company_get_tool(slug: str | None = None) -> dict:
    """Hent innlogga brukar og selskapsinfo frå Fiken.

    Args:
        slug: Valfri overstyring av companySlug. Default brukar FIKEN_COMPANY_SLUG eller første tilgjengelege selskap.
    """
    return await fiken_company_get(_get_client(), slug=slug)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

# Fiken MCP

MCP-server som eksponerer Fiken REST API v2 som verktøy for Claude. Sjå `fiken-mcp-spec.md` for full spec.

## Status: Mini-MVP

Eitt verktøy implementert: `fiken_company_get`. Validerer infrastrukturen (auth, seriell kø, feilhandtering, MCP-protokoll). Resten av Fase 1-verktøya kjem etter at mønsteret er stadfesta mot ekte Fiken-konto.

## Køyre lokalt

```bash
uv sync
cp .env.example .env
# rediger .env med din FIKEN_API_TOKEN

# køyr serveren direkte (stdio-transport)
uv run python -m fiken_mcp.server

# eller via MCP Inspector
npx @modelcontextprotocol/inspector uv run python -m fiken_mcp.server
```

## Claude Desktop

Legg til i `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fiken": {
      "command": "uv",
      "args": ["run", "--directory", "/home/tbri/bc/fikenmcp", "python", "-m", "fiken_mcp.server"],
      "env": {
        "FIKEN_API_TOKEN": "din_token_her",
        "FIKEN_COMPANY_SLUG": "bringsvor-consulting-as"
      }
    }
  }
}
```

import httpx

from fiken_mcp.tools.journal import (
    fiken_journal_entries_list,
    fiken_journal_entry_get,
    fiken_journal_entry_create,
    fiken_transactions_list,
    _in_range,
    _entry_touches_account,
)

SLUG = "test-company"


def _list_response(data):
    return httpx.Response(
        200,
        json=data,
        headers={"fiken-api-result-count": str(len(data)), "fiken-api-page-count": "1"},
    )


# --- Helper functions ---


def test_in_range_within():
    assert _in_range("2026-03-15", "2026-03-01", "2026-03-31") is True


def test_in_range_before():
    assert _in_range("2026-02-28", "2026-03-01", "2026-03-31") is False


def test_in_range_after():
    assert _in_range("2026-04-01", "2026-03-01", "2026-03-31") is False


def test_in_range_no_bounds():
    assert _in_range("2026-01-01", None, None) is True


def test_entry_touches_account_match():
    entry = {"lines": [{"account": "1920", "amount": 100}]}
    assert _entry_touches_account(entry, "1920") is True
    assert _entry_touches_account(entry, "19") is True


def test_entry_touches_account_no_match():
    entry = {"lines": [{"account": "3000", "amount": 100}]}
    assert _entry_touches_account(entry, "1920") is False


# --- Journal entries list ---


async def test_journal_entries_list(client, mock_api):
    entries = [{"journalEntryId": 1, "date": "2026-03-15", "lines": []}]
    mock_api.get(f"/companies/{SLUG}/journalEntries").mock(
        return_value=_list_response(entries)
    )
    result = await fiken_journal_entries_list(client, slug=SLUG)
    assert len(result["data"]) == 1


async def test_journal_entries_list_client_side_date_filter(client, mock_api):
    entries = [
        {"journalEntryId": 1, "date": "2026-02-01", "lines": []},
        {"journalEntryId": 2, "date": "2026-03-15", "lines": []},
    ]
    mock_api.get(f"/companies/{SLUG}/journalEntries").mock(
        return_value=_list_response(entries)
    )
    result = await fiken_journal_entries_list(
        client, slug=SLUG, date_from="2026-03-01", date_to="2026-03-31", fetch_all=True
    )
    assert len(result["data"]) == 1
    assert result["data"][0]["journalEntryId"] == 2


async def test_journal_entries_list_account_filter(client, mock_api):
    entries = [
        {"journalEntryId": 1, "date": "2026-03-15", "lines": [{"account": "1920", "amount": 100}]},
        {"journalEntryId": 2, "date": "2026-03-15", "lines": [{"account": "3000", "amount": 100}]},
    ]
    mock_api.get(f"/companies/{SLUG}/journalEntries").mock(
        return_value=_list_response(entries)
    )
    result = await fiken_journal_entries_list(
        client, slug=SLUG, account="1920", fetch_all=True
    )
    assert len(result["data"]) == 1
    assert result["data"][0]["journalEntryId"] == 1


# --- Journal entry get ---


async def test_journal_entry_get(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/journalEntries/5").respond(
        200, json={"journalEntryId": 5}
    )
    result = await fiken_journal_entry_get(client, 5, slug=SLUG)
    assert result["journalEntryId"] == 5


# --- Journal entry create ---


async def test_journal_entry_create_dry_run(client, mock_api):
    lines = [{"amount": 10000, "account": "1920"}, {"amount": -10000, "account": "3000"}]
    result = await fiken_journal_entry_create(
        client, date="2026-04-16", description="Testbilag", lines=lines, slug=SLUG
    )
    assert result["dry_run"] is True
    assert "10000 øre" in result["summary"]
    assert "1920" in result["summary"]


async def test_journal_entry_create_confirm(client, mock_api):
    route = mock_api.post(f"/companies/{SLUG}/generalJournalEntries").respond(
        201, json={"journalEntryId": 10}
    )
    lines = [{"amount": 5000, "account": "1920"}, {"amount": -5000, "account": "3000"}]
    result = await fiken_journal_entry_create(
        client, date="2026-04-16", description="Bilag", lines=lines, slug=SLUG, confirm=True
    )
    assert result == {"journalEntryId": 10}

    import json as _json

    sent = _json.loads(route.calls.last.request.content)
    assert sent["journalEntries"] == [
        {
            "description": "Bilag",
            "date": "2026-04-16",
            "lines": [{"amount": 5000, "debitAccount": "1920", "creditAccount": "3000"}],
        }
    ]


async def test_journal_entry_create_rejects_long_description(client, mock_api):
    """Fiken prefixes API entries and caps the total at 200 chars — catch it in dry-run."""
    from fiken_mcp.tools.journal import MAX_DESCRIPTION

    lines = [{"amount": 5000, "account": "1920"}, {"amount": -5000, "account": "3000"}]
    result = await fiken_journal_entry_create(
        client,
        date="2026-04-16",
        description="x" * (MAX_DESCRIPTION + 1),
        lines=lines,
        slug=SLUG,
    )
    assert result["error"] is True
    assert str(MAX_DESCRIPTION) in result["message"]


def test_to_fiken_lines_pairs_single_debit_and_credit():
    """The common two-account entry collapses to one Fiken line."""
    from fiken_mcp.tools.journal import _to_fiken_lines

    lines = [{"amount": 180000, "account": "2241"}, {"amount": -180000, "account": "2250"}]
    assert _to_fiken_lines(lines) == [
        {"amount": 180000, "debitAccount": "2241", "creditAccount": "2250"}
    ]


def test_to_fiken_lines_splits_multi_leg_entry():
    """More than one leg per side becomes separate debit-only/credit-only lines."""
    from fiken_mcp.tools.journal import _to_fiken_lines

    lines = [
        {"amount": 80000, "account": "2400"},
        {"amount": -72240, "account": "8151", "vatCode": "0"},
        {"amount": -7760, "account": "7770"},
    ]
    assert _to_fiken_lines(lines) == [
        {"amount": 80000, "debitAccount": "2400"},
        {"amount": 72240, "creditAccount": "8151", "creditVatCode": 0},
        {"amount": 7760, "creditAccount": "7770"},
    ]


async def test_journal_entry_create_unbalanced_rejected():
    """Unbalanced journal entry is rejected before any HTTP call."""
    from fiken_mcp.config import Settings
    from fiken_mcp.client import FikenClient

    settings = Settings(api_token="x", company_slug="co")
    c = FikenClient(settings)
    lines = [{"amount": 10000, "account": "1920"}, {"amount": -5000, "account": "3000"}]
    result = await fiken_journal_entry_create(
        c, date="2026-04-16", description="Feil", lines=lines, slug="co"
    )
    assert result["error"] is True
    assert "balansert" in result["message"]
    await c.aclose()


async def test_journal_entry_create_too_few_lines():
    from fiken_mcp.config import Settings
    from fiken_mcp.client import FikenClient

    settings = Settings(api_token="x", company_slug="co")
    c = FikenClient(settings)
    lines = [{"amount": 0, "account": "1920"}]
    result = await fiken_journal_entry_create(
        c, date="2026-04-16", description="Feil", lines=lines, slug="co"
    )
    assert result["error"] is True
    assert "minst to" in result["message"]
    await c.aclose()

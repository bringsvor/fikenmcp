import base64

import httpx

from fiken_mcp.tools.attachments import (
    fiken_invoice_attachments_list,
    fiken_invoice_attachment_add,
    fiken_journal_entry_attachments_list,
    fiken_journal_entry_attachment_add,
)

SLUG = "test-company"
SAMPLE_PDF = base64.b64encode(b"%PDF-1.4 fake content").decode()


# ── Faktura-vedlegg ────────────────────────────────────────────────────────


async def test_invoice_attachments_list(client, mock_api):
    attachments = [{"filename": "faktura.pdf", "url": "/attachments/1"}]
    mock_api.get(f"/companies/{SLUG}/invoices/42/attachments").respond(
        200, json=attachments
    )
    result = await fiken_invoice_attachments_list(client, 42, slug=SLUG)
    assert result["total"] == 1
    assert result["data"][0]["filename"] == "faktura.pdf"


async def test_invoice_attachments_list_empty(client, mock_api):
    mock_api.get(f"/companies/{SLUG}/invoices/42/attachments").respond(200, json=[])
    result = await fiken_invoice_attachments_list(client, 42, slug=SLUG)
    assert result["data"] == []
    assert result["total"] == 0


async def test_invoice_attachment_add_dry_run(client, mock_api):
    result = await fiken_invoice_attachment_add(
        client, 42, filename="rapport.pdf", content_base64=SAMPLE_PDF, slug=SLUG
    )
    assert result["dry_run"] is True
    assert "rapport.pdf" in result["summary"]
    assert "faktura 42" in result["summary"]


async def test_invoice_attachment_add_confirm(client, mock_api):
    mock_api.post(f"/companies/{SLUG}/invoices/42/attachments").respond(201, json={})
    result = await fiken_invoice_attachment_add(
        client, 42, filename="rapport.pdf", content_base64=SAMPLE_PDF,
        slug=SLUG, confirm=True,
    )
    assert result == {}


async def test_invoice_attachment_add_invalid_base64(client, mock_api):
    result = await fiken_invoice_attachment_add(
        client, 42, filename="bad.pdf", content_base64="!!!not-base64!!!",
        slug=SLUG, confirm=True,
    )
    assert result["error"] is True
    assert "base64" in result["message"].lower()


# ── Bilagsvedlegg ──────────────────────────────────────────────────────────


async def test_journal_entry_attachments_list(client, mock_api):
    attachments = [{"filename": "bilag.pdf", "url": "/attachments/2"}]
    mock_api.get(f"/companies/{SLUG}/journalEntries/10/attachments").respond(
        200, json=attachments
    )
    result = await fiken_journal_entry_attachments_list(client, 10, slug=SLUG)
    assert result["total"] == 1
    assert result["data"][0]["filename"] == "bilag.pdf"


async def test_journal_entry_attachment_add_dry_run(client, mock_api):
    result = await fiken_journal_entry_attachment_add(
        client, 10, filename="kvittering.jpg", content_base64=SAMPLE_PDF, slug=SLUG
    )
    assert result["dry_run"] is True
    assert "kvittering.jpg" in result["summary"]
    assert "bilag 10" in result["summary"]


async def test_journal_entry_attachment_add_confirm(client, mock_api):
    mock_api.post(f"/companies/{SLUG}/journalEntries/10/attachments").respond(
        201, json={}
    )
    result = await fiken_journal_entry_attachment_add(
        client, 10, filename="kvittering.jpg", content_base64=SAMPLE_PDF,
        slug=SLUG, confirm=True,
    )
    assert result == {}

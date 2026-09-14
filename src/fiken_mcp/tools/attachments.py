import base64
from typing import Any

from ..client import FikenClient


async def _slug(client: FikenClient, slug: str | None) -> str | dict[str, Any]:
    return slug or await client.get_company_slug()


# ── Fil-nedlasting ────────────────────────────────────────────────────────


async def fiken_file_download(
    client: FikenClient, url: str
) -> dict[str, Any]:
    """Last ned fil frå Fiken API-URL. Returnerer base64-innhald + metadata."""
    if not url:
        return {
            "error": True,
            "status_code": 400,
            "message": "URL er påkravd",
            "fiken_error": None,
        }

    file_bytes, content_type, error = await client.download_file(url)
    if error is not None:
        return error

    filename = url.rsplit("/", 1)[-1] if "/" in url else "file"

    return {
        "filename": filename,
        "content_type": content_type,
        "size_bytes": len(file_bytes),
        "content_base64": base64.b64encode(file_bytes).decode(),
    }


# ── Faktura-vedlegg ────────────────────────────────────────────────────────


async def fiken_invoice_attachments_list(
    client: FikenClient, invoice_id: int, *, slug: str | None = None
) -> dict[str, Any]:
    """List vedlegg på ein faktura."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved
    result = await client.request(
        "GET", f"/companies/{resolved}/invoices/{invoice_id}/attachments"
    )
    if isinstance(result, list):
        return {"data": result, "total": len(result)}
    return result


async def fiken_invoice_attachment_add(
    client: FikenClient,
    invoice_id: int,
    *,
    filename: str,
    content_base64: str,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Legg til vedlegg på ein faktura. Filinnhald som base64-streng. Krev confirm=True."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    try:
        file_bytes = base64.b64decode(content_base64)
    except Exception as exc:
        return {
            "error": True,
            "status_code": 400,
            "message": f"Ugyldig base64-innhald: {exc}",
            "fiken_error": None,
        }

    if not confirm:
        return {
            "dry_run": True,
            "operation": f"POST /invoices/{invoice_id}/attachments",
            "summary": f"Vil laste opp '{filename}' ({len(file_bytes)} bytes) til faktura {invoice_id}",
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    return await client.request(
        "POST",
        f"/companies/{resolved}/invoices/{invoice_id}/attachments",
        files={"file": (filename, file_bytes)},
        data={"filename": filename},
    )


# ── Bilagsvedlegg ──────────────────────────────────────────────────────────


async def fiken_journal_entry_attachments_list(
    client: FikenClient, journal_entry_id: int, *, slug: str | None = None
) -> dict[str, Any]:
    """List vedlegg på eit bilag."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved
    result = await client.request(
        "GET", f"/companies/{resolved}/journalEntries/{journal_entry_id}/attachments"
    )
    if isinstance(result, list):
        return {"data": result, "total": len(result)}
    return result


async def fiken_journal_entry_attachment_add(
    client: FikenClient,
    journal_entry_id: int,
    *,
    filename: str,
    content_base64: str,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Legg til vedlegg på eit bilag. Filinnhald som base64-streng. Krev confirm=True."""
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    try:
        file_bytes = base64.b64decode(content_base64)
    except Exception as exc:
        return {
            "error": True,
            "status_code": 400,
            "message": f"Ugyldig base64-innhald: {exc}",
            "fiken_error": None,
        }

    if not confirm:
        return {
            "dry_run": True,
            "operation": f"POST /journalEntries/{journal_entry_id}/attachments",
            "summary": f"Vil laste opp '{filename}' ({len(file_bytes)} bytes) til bilag {journal_entry_id}",
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    return await client.request(
        "POST",
        f"/companies/{resolved}/journalEntries/{journal_entry_id}/attachments",
        files={"file": (filename, file_bytes)},
        data={"filename": filename},
    )

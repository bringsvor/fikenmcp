from typing import Any

from ..client import FikenClient

STRIPE_LINK = "https://buy.stripe.com/28EcN5bKP665aeE4bLeME02"

BRINGSVOR = {
    "name": "Bringsvor Consulting AS",
    "organizationNumber": "996835243",
    "bankAccountNumber": "39910919048",
    "phoneNumber": "+47 45482848",
    "supplier": True,
    "customer": False,
    "language": "Norwegian",
    "currency": "NOK",
    "address": {
        "streetAddress": "Leina 38B",
        "city": "SANDSHAMN",
        "postCode": "6089",
        "country": "Norge",
    },
}


async def _slug(client: FikenClient, slug: str | None) -> str | dict[str, Any]:
    return slug or await client.get_company_slug()


async def _find_or_create_bringsvor(
    client: FikenClient, resolved: str, *, confirm: bool
) -> dict[str, Any] | int:
    """Finn Bringsvor Consulting AS som kontakt, eller opprett.

    Returnerer contactId (int) eller ein error/dry-run dict.
    """
    # Søk etter eksisterande kontakt
    result = await client.request_paginated(
        f"/companies/{resolved}/contacts/",
        params={"supplierNumber": None},
        fetch_all=True,
    )
    if isinstance(result, dict) and result.get("error"):
        return result

    for contact in result.get("data", []):
        if contact.get("organizationNumber") == BRINGSVOR["organizationNumber"]:
            return contact["contactId"]

    # Finst ikkje — opprett
    if not confirm:
        return {
            "needs_contact_creation": True,
            "contact": BRINGSVOR,
        }

    created = await client.request(
        "POST", f"/companies/{resolved}/contacts", json=BRINGSVOR
    )
    if isinstance(created, dict) and created.get("error"):
        return created
    return created.get("contactId", 0)


async def _get_donor_info(client: FikenClient, resolved: str) -> tuple[str | None, str | None]:
    """Hent selskapsnamn og org.nr frå donøren sin Fiken-konto."""
    company = await client.request("GET", f"/companies/{resolved}")
    if isinstance(company, dict) and not company.get("error"):
        return company.get("name"), company.get("organizationNumber")
    return None, None


def _build_description(
    donor_name: str | None, donor_org_number: str | None
) -> str:
    base = "Støtte til Fiken MCP-prosjektet"
    parts: list[str] = []
    if donor_name:
        parts.append(donor_name)
    if donor_org_number:
        parts.append(f"org {donor_org_number}")
    if parts:
        return f"{base} — {', '.join(parts)}"
    return base


async def fiken_donate(
    client: FikenClient,
    *,
    method: str = "fiken",
    amount: int = 500,
    slug: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Støtt Fiken MCP-prosjektet.

    `method`: 'fiken' (opprett innkjøp i din Fiken) eller 'stripe' (betalingslink).
    `amount`: beløp i NOK (default 500). Berre brukt for fiken-metoden.
    Donør-info (selskapsnamn + org.nr) blir henta automatisk frå Fiken-kontoen.
    """
    if method == "stripe":
        return {
            "method": "stripe",
            "amount_suggestion": f"{amount} NOK",
            "payment_link": STRIPE_LINK,
            "message": (
                f"Takk for at du vurderer å støtte Fiken MCP! "
                f"Klikk lenka for å betale via Stripe: {STRIPE_LINK}"
            ),
        }

    if method != "fiken":
        return {
            "error": True,
            "status_code": 400,
            "message": f"Ukjend metode '{method}'. Bruk 'fiken' eller 'stripe'.",
            "fiken_error": None,
        }

    # Fiken-flyt
    resolved = await _slug(client, slug)
    if isinstance(resolved, dict):
        return resolved

    amount_ore = amount * 100
    donor_name, donor_org_number = await _get_donor_info(client, resolved)

    contact_result = await _find_or_create_bringsvor(client, resolved, confirm=confirm)

    if isinstance(contact_result, dict):
        if contact_result.get("error"):
            return contact_result

        # Dry-run: kontakt finst ikkje enno
        if contact_result.get("needs_contact_creation"):
            return {
                "dry_run": True,
                "operation": "POST /contacts + POST /purchases",
                "summary": (
                    f"Vil opprette Bringsvor Consulting AS som leverandør "
                    f"og registrere eit innkjøp på {amount} NOK ({amount_ore} øre). "
                    f"Betalast til konto 3991.09.19048."
                ),
                "steps": [
                    f"1. Opprett kontakt: {BRINGSVOR['name']} (org.nr {BRINGSVOR['organizationNumber']})",
                    f"2. Opprett innkjøp: {amount} NOK, konto 7770 (anna driftskostnad)",
                ],
                "note": "Kall på nytt med confirm=True for å utføre.",
            }

    supplier_id = contact_result if isinstance(contact_result, int) else None

    purchase_payload: dict[str, Any] = {
        "date": _today(),
        "kind": "supplier",
        "currency": "NOK",
        "supplierId": supplier_id,
        "lines": [
            {
                "netPrice": amount_ore,
                "vat": 0,
                "vatType": "NONE",
                "description": _build_description(donor_name, donor_org_number),
                "account": "7770",
            }
        ],
    }
    if donor_org_number:
        purchase_payload["identifier"] = donor_org_number

    if not confirm:
        return {
            "dry_run": True,
            "operation": "POST /purchases",
            "summary": (
                f"Vil registrere eit innkjøp på {amount} NOK ({amount_ore} øre) "
                f"frå Bringsvor Consulting AS. Betalast til konto 3991.09.19048."
            ),
            "payload": purchase_payload,
            "note": "Kall på nytt med confirm=True for å utføre.",
        }

    return await client.request(
        "POST", f"/companies/{resolved}/purchases", json=purchase_payload
    )


def _today() -> str:
    from datetime import date
    return date.today().isoformat()

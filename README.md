# window-cleaning-crm

Portfolio Django **site-plus-CRM** for a solo residential window-cleaning business (fictional demo brand: Lakeside Pane Co.).

This is a single-tenant Django monolith: a polished marketing site living alongside an owner CRM that covers the residential loop — leads → quotes → jobs → invoices → review ask → recurring offer. It is **not** a live customer site. A real owner site (Webflow/Squarespace or a real domain) should be able to replace the dummy marketing site later without rewriting the CRM.

## Stack

- Django 5.x / Python 3.12
- Postgres
- Server-rendered templates + a little HTMX
- Single owner login (phone-simple owner UI; Django admin may exist for bootstrap only)

## Modular apps

| App | Role |
|---|---|
| `accounts` | Single owner authentication + owner home |
| `marketing` | Dummy/portfolio public site (home, services, service area, about, gallery, FAQ, contact/quote) |
| `leads` | Public quote form, phone-lead entry, owner list/detail, inbound webhook |
| `clients` | Customer + one Property / service address; access notes; nullable commercial future-proof fields |
| `quoting` | Editable rate card + itemized quotes; send / accept / lose |
| `jobs` | Schedule / weather hold / complete / private photos |
| `billing` | Invoices from jobs + cash/check/Venmo/other; Stripe URL placeholder |
| `followup` | Review ask + recurring offer (later) |
| `notifications` | Email path used for leads; **SMS is a stub** |

## Stubs (explicit)

- **Stripe:** placeholder fields only in later PRs — no SDK, no charges, no card vault.
- **SMS:** `notifications.sms.send(to, body)` logs or no-ops. Email is the demo notification path.
- **Live owner site:** keep `marketing` isolated. A future Webflow/Squarespace form can `POST /integrations/leads/` with header `X-Leads-Webhook-Secret` (value from `LEADS_WEBHOOK_SECRET`).

## Demo copy (static; not `seed_demo`)

- Brand: Lakeside Pane Co.
- Owner persona: Jordan Hale
- Area: Cedar Falls, Waterloo & nearby ZIPs (Central Time)
- Phone: (555) 010-2040
- Gallery / owner images are labeled fictional SVG placeholders — not real people or customers.

## Local setup

Requirements: Python 3.12, Docker (for Postgres), and a virtualenv.

```bash
cp .env.example .env
docker compose up -d db
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # bootstrap owner login
python manage.py runserver
```

Public site:

- Home: `/`
- Quote form POST: `/quote/` (also linked from `/contact/` and `/quote/` pages)
- Services / area / about / gallery / FAQ / contact: `/services/`, `/service-area/`, `/about/`, `/gallery/`, `/faq/`, `/contact/`

Owner UI:

- Login: `/login/`
- Owner home: `/owner/`
- Leads: `/owner/leads/`
- Log phone lead: `/owner/leads/new/`
- Django admin (bootstrap only): `/admin/`

Inbound webhook (for a future live site):

- `POST /integrations/leads/`
- Header: `X-Leads-Webhook-Secret: <LEADS_WEBHOOK_SECRET>`
- JSON body fields: `name` (required), `email`, `phone`, `address`/`address_line1`, `city`, `zip_code`, `service_interest`, `stories`, `window_pane_estimate`, `how_heard`, `message`
- Lead photos are private: served only at `/owner/leads/<id>/photos/<photo_id>/` when logged in (not via public `/media/`).

Pinned dependencies also live in `requirements.lock` (same pins as `requirements.txt` for this scaffold).

## Tests / CI

```bash
python manage.py check
python manage.py test
```

GitHub Actions runs the same checks against Postgres on every pull request.

## Owner CRM (PR 3)

- Customers: `/owner/clients/`
- Quotes: `/owner/quotes/`
- Rate card: `/owner/quotes/rate-card/`
- Build a quote from a lead: `/owner/quotes/from-lead/<lead_id>/`
- Accept creates Customer + one Property + Job and marks the lead won
- Jobs: `/owner/jobs/`
- Invoices: `/owner/invoices/`

## What this PR does / does not

**PR 5 (invoices + payments):** Invoice/InvoiceLine from a job's quote (snapshotted totals); Payment (cash/check/Venmo/other) with provider/external_id stubs; nullable `hosted_payment_url` placeholder (no Stripe SDK/charges).

**Not in this PR:** Stripe SDK/charges/webhooks, review-ask, recurring offer, live SMS, `seed_demo`, or production deploy.

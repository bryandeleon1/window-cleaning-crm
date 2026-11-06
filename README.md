# window-cleaning-crm

Portfolio Django **site-plus-CRM** for a solo residential window-cleaning business (fictional demo brand: Lakeside Pane Co.).

This is a single-tenant Django monolith: a polished marketing site (later PRs) living alongside an owner CRM that covers the residential loop — leads → quotes → jobs → invoices → review ask → recurring offer. It is **not** a live customer site. A real owner site (Webflow/Squarespace or a real domain) should be able to replace the dummy marketing site later without rewriting the CRM.

## Stack

- Django 5.x / Python 3.12
- Postgres
- Server-rendered templates + a little HTMX
- Single owner login (phone-simple owner UI; Django admin may exist for bootstrap only)

## Modular apps

| App | Role |
|---|---|
| `accounts` | Single owner authentication + owner home stub |
| `marketing` | Dummy/portfolio public site (later) |
| `leads` | Public quote form + phone-lead entry (later) |
| `clients` | Customer + property (later) |
| `quoting` | Rate card + itemized quotes (later) |
| `jobs` | Schedule / complete / photos (later) |
| `billing` | Invoices + payment recording (later) |
| `followup` | Review ask + recurring offer (later) |
| `notifications` | Email path later; **SMS is a stub** today |

## Stubs (explicit)

- **Stripe:** placeholder fields only in later PRs — no SDK, no charges, no card vault.
- **SMS:** `notifications.sms.send(to, body)` logs or no-ops. Email is the demo notification path.
- **Live owner site:** marketing stays isolated; inbound webhook for a future Webflow/Squarespace form arrives in a later PR.

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

Owner UI:

- Login: `/login/`
- Owner home stub: `/owner/`
- Django admin (bootstrap only): `/admin/`

Pinned dependencies also live in `requirements.lock` (same pins as `requirements.txt` for this scaffold).

## Tests / CI

```bash
python manage.py check
python manage.py test
```

GitHub Actions runs the same checks against Postgres on every pull request.

## What this PR does / does not

**PR 1 (this scaffold):** project package `config`, env-based settings, all nine apps installed, `accounts` login/logout + owner home, SMS stub, base HTMX-ready template, docker-compose Postgres, CI, README.

**Not in this PR:** `seed_demo`, marketing site, lead form, quotes, jobs, invoices, review-ask, recurring offer, Stripe, or production deploy.

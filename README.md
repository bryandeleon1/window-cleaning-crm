# window-cleaning-crm

Portfolio Django **site-plus-CRM** for a solo residential window-cleaning business (fictional demo brand: **Lakeside Pane Co.**).

This is a single-tenant Django monolith: a polished marketing site living alongside an owner CRM that covers the residential loop:

**leads → quotes → jobs → invoices → review ask → recurring offer**

It is **not** a live customer site. A real owner site (Webflow/Squarespace or a real domain) should be able to replace the dummy marketing site later without rewriting the CRM.

**Demo URL:** not hosted yet.

## Stack

- Django 5.x / Python 3.12
- Postgres
- Server-rendered templates
- Gunicorn + WhiteNoise for a generic production process
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
| `followup` | Review-ask email + recurring offer (frequency / next date / optional discount) |
| `notifications` | Email is the demo path; **SMS is a stub** |

## Local setup

Requirements: Python 3.12, Docker (for Postgres), and a virtualenv.

```bash
cp .env.example .env
docker compose up -d db
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

### Demo owner login (from `seed_demo`)

| | |
|---|---|
| Username | `jordan` |
| Password | `demo-pass-12345` |
| Persona | Jordan Hale (fictional) |

`seed_demo` is **idempotent** — safe to re-run. It loads a full fictional residential loop (no real customer PII): rate card, inbound-style accepted quote → customer + property + job, a completed job with invoice + Venmo payment, a review-ask email, a biannual recurring plan, a weather-hold job, plus extra new/lost leads.

## Owner CRM URLs

| Area | Path |
|---|---|
| Login | `/login/` |
| Owner home | `/owner/` |
| Leads | `/owner/leads/` |
| Log phone lead | `/owner/leads/new/` |
| Customers | `/owner/clients/` |
| Quotes | `/owner/quotes/` |
| Rate card | `/owner/quotes/rate-card/` |
| Build quote from lead | `/owner/quotes/from-lead/<lead_id>/` |
| Jobs | `/owner/jobs/` |
| Invoices | `/owner/invoices/` |
| Follow-up | `/owner/followup/` |
| Django admin (bootstrap only) | `/admin/` |

## Public marketing site

- Home: `/`
- Services / area / about / gallery / FAQ / contact: `/services/`, `/service-area/`, `/about/`, `/gallery/`, `/faq/`, `/contact/`
- Quote form POST: `/quote/`

Demo copy (swap without a migration): Lakeside Pane Co.; Jordan Hale; Cedar Falls, Waterloo & nearby ZIPs (Central Time); phone `(555) 010-2040`. Gallery/owner images are labeled fictional SVG placeholders.

## Stubs (explicit — as implemented)

- **Stripe:** placeholder fields only — `Invoice.hosted_payment_url`, `Payment.provider`, `Payment.external_id`. **No** Stripe SDK, charges, webhooks, or card vault. Saving a hosted URL does not charge anyone.
- **SMS:** `notifications.sms.send(to, body)` logs or no-ops. **Email** is the demo notification path (leads, quotes, review asks).
- **Live owner site:** keep `marketing` isolated. A future Webflow/Squarespace form can post into the same CRM:

```http
POST /integrations/leads/
X-Leads-Webhook-Secret: <LEADS_WEBHOOK_SECRET>
Content-Type: application/json
```

JSON fields: `name` (required), `email`, `phone`, `address`/`address_line1`, `city`, `zip_code`, `service_interest`, `stories`, `window_pane_estimate`, `how_heard`, `message`.

## Private photos

Lead and job photos are **private**. They are served only through login-required owner URLs (e.g. `/owner/leads/<id>/photos/<photo_id>/`, `/owner/jobs/<id>/photos/<photo_id>/`). There is **no** public `/media/` route. The optional `use_in_gallery` flag on job photos is stored only — it does not auto-publish to the marketing gallery.

## Security notes

This is a single-owner portfolio demo. The notes below summarize what is already locked down, what this security pass changed, and which simpler choices were left in place on purpose.

### What is already protected

- Owner screens and photo routes require a login. Someone who is not signed in cannot view or change CRM records or photos.
- Browser forms, including logout, use Django's CSRF protection so a forged cross-site form post is rejected.
- Lead and job photos are checked on upload (allowed image types, size, and dimensions). They are served only on private owner URLs. When a stored file is retrieved, the app inspects the bytes again and returns 404 rather than serving unknown or unsafe content, and it sends `X-Content-Type-Options: nosniff` so the browser does not guess a different file type.
- The inbound lead webhook (`POST /integrations/leads/`) requires a shared secret in the `X-Leads-Webhook-Secret` header. If the configured secret is unset or empty, the webhook fails closed (requests are rejected even if a header is sent).
- There is no public `/media/` route, so uploaded files are not exposed as static URLs.
- `.env` is listed in `.gitignore` (and `.dockerignore`), so local secrets are not committed.

### What this security pass changed

- The webhook secret is compared with `hmac.compare_digest` (a constant-time comparison) instead of a plain `==`, which avoids leaking information about the secret through timing.
- Unused HTMX `<script>` tags that loaded JavaScript from the unpkg CDN were removed from the base templates. The app does not load third-party JavaScript until a feature actually uses it.

### Accepted tradeoffs

These simpler choices are intentional for a laptop/portfolio demo, not oversights:

- The default `SECRET_KEY` is an insecure local-only value so the app can boot without a `.env` file. A real deployment must set its own secret key.
- `DEBUG` defaults to `False`.
- `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, and `SECURE_SSL_REDIRECT` are left unset so local HTTP works, including Docker on port 8000. Enabling them would break that local HTTP setup.
- There are no rate limits, two-factor authentication, or a Content Security Policy. Those would be extra ceremony for a single-owner portfolio demo.
- The webhook view is marked `csrf_exempt` because it is a machine-to-machine POST, not a browser form. The shared-secret header stands in for CSRF, and an empty secret fails closed.
- There is no extra rate limit on the webhook or on the public quote request form.
- `/admin/` stays available as Django's built-in admin tool. The product UI lives under login-only `/owner/`.
- The app is single-tenant: any logged-in owner can see all records. There are no per-record permissions.
- The Dockerfile sets a build-time secret key only so `collectstatic` can run during the image build. Runtime must override that key through the environment or a `.env` file.
- The Compose Postgres username and password are laptop demo defaults. They are not suitable for a public host.
- The seed owner login is a known fictional demo credential, documented in the "Demo owner login" section above. Change it before any real deployment.
- An invoice's hosted payment URL is stored in a Django `URLField`, which already requires `http://` or `https://`. There is no extra domain allowlist, because Stripe Payment Link domains vary. Only a logged-in owner pastes this URL, and saving it does not charge anyone.

## How to swap the dummy marketing site later

1. Leave the CRM apps (`leads`, `clients`, `quoting`, `jobs`, `billing`, `followup`, `accounts`) as-is.
2. Point your live site’s form (or Zapier) at `POST /integrations/leads/` with the shared-secret header.
3. Stop routing public traffic to the `marketing` app URLs, or replace those templates/static assets. The CRM does not depend on the dummy site’s pages.

## Tests / CI

```bash
python manage.py check
python manage.py test
```

GitHub Actions runs the same checks against Postgres on every pull request.

## Generic deploy config (no host yet)

This repo does **not** sign you up for Render, Fly, Railway, Heroku, or any other host. There is no live demo URL.

Production-oriented pieces included:

- `Dockerfile` — Python 3.12, `collectstatic`, `gunicorn config.wsgi:application`
- `docker-compose.yml` — `db` (Postgres) + optional `web` service
- WhiteNoise so gunicorn can serve static files without a CDN/S3
- `.env.example` — production checklist comments

Typical process on whatever host you choose later:

```bash
# set DEBUG=False, SECRET_KEY, DATABASE_URL, ALLOWED_HOSTS,
# email settings, LEADS_WEBHOOK_SECRET — never commit .env
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_demo   # optional fictional demo data
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

Or with Compose (after copying `.env`):

```bash
docker compose up --build
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py seed_demo
```

## What PR 7 does / does not

**PR 7 (last planned slice):** `seed_demo`, README polish for the full loop, generic Dockerfile/compose/`gunicorn`+WhiteNoise deploy config. Demo URL: not hosted yet.

**Not in this PR:** merging earlier PRs; provisioning a host; live Stripe/SMS/Google APIs; real customer data; extra product features.

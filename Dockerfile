# Generic production-ish image for the window-cleaning CRM.
# Does not target a specific host (Render/Fly/Railway/Heroku).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collectstatic needs env vars; use safe placeholders at build time.
# The build-time SECRET_KEY exists only for collectstatic; runtime must override it via env / .env.
ENV DEBUG=False \
    SECRET_KEY=build-time-only-not-for-runtime \
    ALLOWED_HOSTS=localhost \
    DATABASE_URL=postgres://wccrm:wccrm@db:5432/wccrm \
    EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]

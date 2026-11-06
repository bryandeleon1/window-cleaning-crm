"""Login-only private photo responses."""

from django.http import FileResponse, Http404

from .images import sniff_image_content_type


def private_image_response(field_file):
    if not field_file:
        raise Http404("Photo missing.")
    try:
        fh = field_file.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        raise Http404("Photo missing.")
    content_type = sniff_image_content_type(fh)
    if content_type is None:
        fh.close()
        raise Http404("Photo unavailable.")
    fh.seek(0)
    response = FileResponse(fh, content_type=content_type)
    response["X-Content-Type-Options"] = "nosniff"
    return response

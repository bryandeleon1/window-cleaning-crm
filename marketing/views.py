"""Public marketing pages for the fictional Lakeside Pane Co. demo. Static copy only;
the quote request form posts to leads.views.public_quote.
"""

from django.views.generic import TemplateView

from leads.forms import PublicQuoteForm

from . import demo


class MarketingContextMixin:
    """Shared demo copy for marketing templates."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "brand_name": demo.BRAND_NAME,
                "owner_name": demo.OWNER_NAME,
                "phone_display": demo.PHONE_DISPLAY,
                "phone_tel": demo.PHONE_TEL,
                "time_zone_label": demo.TIME_ZONE_LABEL,
                "service_area_cities": demo.SERVICE_AREA_CITIES,
                "service_area_zips": demo.SERVICE_AREA_ZIPS,
                "core_services": demo.CORE_SERVICES,
                "addon_services": demo.ADDON_SERVICES,
                "not_offered": demo.NOT_OFFERED,
                "faq_items": demo.FAQ_ITEMS,
            }
        )
        return context


class HomeView(MarketingContextMixin, TemplateView):
    template_name = "marketing/home.html"


class ServicesView(MarketingContextMixin, TemplateView):
    template_name = "marketing/services.html"


class ServiceAreaView(MarketingContextMixin, TemplateView):
    template_name = "marketing/service_area.html"


class AboutView(MarketingContextMixin, TemplateView):
    template_name = "marketing/about.html"


class GalleryView(MarketingContextMixin, TemplateView):
    template_name = "marketing/gallery.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["gallery_images"] = [
            "marketing/img/gallery-1.svg",
            "marketing/img/gallery-2.svg",
            "marketing/img/gallery-3.svg",
            "marketing/img/gallery-4.svg",
        ]
        return context


class FAQView(MarketingContextMixin, TemplateView):
    template_name = "marketing/faq.html"


class ContactView(MarketingContextMixin, TemplateView):
    template_name = "marketing/contact.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = PublicQuoteForm()
        return context

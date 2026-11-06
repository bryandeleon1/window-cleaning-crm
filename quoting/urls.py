from django.urls import path

from . import views

app_name = "quoting"

urlpatterns = [
    path("", views.quote_list, name="list"),
    path("rate-card/", views.rate_card_edit, name="rate_card"),
    path("rate-card/items/<int:item_id>/", views.rate_card_item_edit, name="rate_card_item_edit"),
    path("from-lead/<int:lead_id>/", views.build_from_lead, name="build_from_lead"),
    path("<int:pk>/", views.quote_detail, name="detail"),
    path("<int:pk>/send/", views.send_quote, name="send"),
    path("<int:pk>/accept/", views.accept, name="accept"),
    path("<int:pk>/lose/", views.lose, name="lose"),
]

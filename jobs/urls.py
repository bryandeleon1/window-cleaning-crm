from django.urls import path

from . import views

app_name = "jobs"

urlpatterns = [
    path("", views.job_list, name="list"),
    path("<int:pk>/", views.job_detail, name="detail"),
    path("<int:pk>/schedule/", views.job_schedule, name="schedule"),
    path("<int:pk>/weather-hold/", views.job_weather_hold, name="weather_hold"),
    path("<int:pk>/complete/", views.job_complete, name="complete"),
    path("<int:pk>/photos/upload/", views.job_photo_upload, name="photo_upload"),
    path("<int:pk>/photos/<int:photo_id>/", views.job_photo, name="photo"),
]

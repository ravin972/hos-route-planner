from django.urls import path

from .views import HealthView, LocationSearchView, PlanView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("trips/plan", PlanView.as_view(), name="trips-plan"),
    path("locations/search", LocationSearchView.as_view(), name="locations-search"),
]

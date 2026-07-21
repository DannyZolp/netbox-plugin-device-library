"""URL patterns for the Device Library plugin."""

from django.urls import path

from . import views

urlpatterns = (
    path("settings/", views.SettingsView.as_view(), name="settings"),
    path("settings/sync/", views.SyncAllLibrariesView.as_view(), name="sync_all"),
    path("settings/library-search/", views.LibrarySearchView.as_view(), name="library_search"),
)

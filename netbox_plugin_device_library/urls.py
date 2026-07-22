"""URL patterns for the Device Library plugin."""

from django.urls import path

from . import views

urlpatterns = (
    path("settings/", views.SettingsView.as_view(), name="settings"),
    path("settings/sync/", views.SyncAllLibrariesView.as_view(), name="sync_all"),
    path("settings/library-search/", views.LibrarySearchView.as_view(), name="library_search"),
    path(
        "library/<str:object_type>/<int:pk>/import/",
        views.QueueLibraryObjectImportView.as_view(),
        name="queue_library_object_import",
    ),
    path(
        "library/import-jobs/<int:pk>/",
        views.LibraryObjectImportStatusView.as_view(),
        name="library_object_import_status",
    ),
)

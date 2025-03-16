from django.urls import path

from . import views

urlpatterns = [
    path("webvirtcloud/<mac>/meta-data", views.os_metadata_for_mac, name="ds_nocloud_metadata_for_mac"),
    path("vdi/<int:compute_id>/<vname>/", views.get_vdi_url, name="vdi_url"),
]

from django.conf import settings
from django.urls import include, path, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from appsettings.views import appsettings
from console.views import console
from instances.views import index
from mozilla_django_oidc import views as oidc_views


schema_view = get_schema_view(
   openapi.Info(
      title="Webvirtcloud REST-API",
      default_version='v1',
      description="Webvirtcloud REST API",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="catborise@gmail.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("", index, name="index"),
    path("admin/", include(("admin.urls", "admin"), namespace="admin")),
    path("accounts/", include("accounts.urls")),
    path("appsettings/", appsettings, name="appsettings"),
    path("computes/", include("computes.urls")),
    path("console/", console, name="console"),
    path("datasource/", include("datasource.urls")),
    path("instances/", include("instances.urls")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("logs/", include("logs.urls")),
    path("oidc/authenticate/", oidc_views.OIDCAuthenticationRequestView.as_view(), name="oidc_authentication_init"),
    path("oidc/callback/", oidc_views.OIDCAuthenticationCallbackView.as_view(), name="oidc_authentication_callback"),
    path("oidc/logout/", oidc_views.OIDCLogoutView.as_view(), name="oidc_logout"),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/v1/', include("webvirtcloud.urls-api")),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    try:
        import debug_toolbar

        urlpatterns += [
            path("__debug__/", include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass


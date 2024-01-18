from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles import views as viewsstatic
# from django.conf.urls import include
from django.views import defaults as default_views
from django.urls import (include, re_path, path, )
from django.views.generic.base import RedirectView

from webgis import views


# register URLs for each app + media URLs
urlpatterns = [
                  # re_path(r'^$', views.index, name='index'),
                  # default index page
                  # re_path(r'^$', RedirectView.as_view(url='/mapviewer/detail/1.html'), name='index'),
                  re_path(r'^$', RedirectView.as_view(url='/admin'), name='index'),

                  re_path(r'^session$', views.sessions, name='sessions'),
                  re_path(r'^authapi/', include('authapi.urls')),
                  re_path(r'^mapviewer/', include('mapviewer.urls')),
                  re_path(r'^layers/', include('layers.urls')),
                  re_path(r'^geospatial/', include('geospatial.urls')),
                  re_path(r'^csw/', include('csw.urls')),
                  re_path(r'^phaenopt/', include('phaenopt.urls')),
                  re_path(r'^swos/', include('swos.urls')),
                  # re_path(r'^validation/', include('validation.urls')),
                  re_path(r'^admin/', admin.site.urls),
                  re_path(r'^login/$', auth_views.LoginView.as_view(), name='LoginView'),
                  re_path(r'^climate/', include('climate.urls')),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', viewsstatic.serve),
    ]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
from django.conf import settings
#from django.conf.urls import include
from django.urls import include, re_path
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles import views as viewsstatic
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView
from webgis import views

# register URLs for each app + media URLs
urlpatterns = [
    #re_path(r'^$', views.index, name='index'),
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
    #re_path(r'^validation/', include('validation.urls')),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^login/$', auth_views.LoginView.as_view(), name='LoginView'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 

if settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', viewsstatic.serve),
    ]

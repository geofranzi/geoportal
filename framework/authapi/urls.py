from django.urls import include, re_path
from . import views

import django

from dj_rest_auth.registration.views import VerifyEmailView

urlpatterns = [
    re_path(r'^rest/', include('dj_rest_auth.urls')),
    re_path(r'^rest/setmapid/(?P<pk>[0-9]+)$', views.SetMapId.as_view(), name='set_map_id'),
    re_path(r'^rest/registration/(?P<pk>[0-9]+)$', views.RegisterUser.as_view(), name='rest_register'),
    re_path(r'^rest/registration/verify-email/$', VerifyEmailView.as_view(), name='rest_verify_email'),
    re_path(r"^rest/registration/confirm-email/(?P<key>[-:\w]+)/$", views.VerifyEmail.as_view(), name="account_confirm_email"),
    re_path(r'^rest/password/reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', views.ConfirmPasswordReset.as_view(), name='password_reset_confirm'),
    re_path(r"^rest/user/delete/", views.DeleteUser.as_view(), name="account_delete_user"),
    re_path(r"^rest/registration/confirmation/send$", views.SetMapId.as_view(), name='account_email_verification_sent'),
]

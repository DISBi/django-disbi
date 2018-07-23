"""disbi_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
# Django
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView

from .views import go_to_organism

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name="index.html"), name='index'),
    url(r'^go_to_org/$', go_to_organism, name='go-to-org'),
    url(r'^accounts/login/$', auth_views.login, 
        {'template_name': 'disbi/registration/login.html'}, name='login'),
    url(r'^accounts/logout/$', auth_views.logout, 
        {'template_name': 'disbi/registration/logout.html'}, name='logout'),
    url(r'^accounts/password_change/$', auth_views.password_change,
            {'template_name': 'disbi/registration/password_change_form.html',
             'post_change_redirect': '/accounts/password_change/done/'}, 
            name='password_change'),
    url(r'^accounts/password_change/done/$', auth_views.password_change_done,
            {'template_name': 'disbi/registration/password_change_done.html'}, 
            name='password_change_done'),
    url(r'^accounts/password_reset/$', auth_views.password_reset,
            {'template_name': 'disbi/registration/password_reset_form.html'}, 
            name='password_reset'),
    url(r'^accounts/password_reset/done/$', auth_views.password_reset_done,
            {'template_name': 'disbi/registration/password_reset_done.html'}, 
            name='password_reset_done'),
    url(r'^accounts/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', 
        auth_views.password_reset_confirm,
            {'template_name': 'disbi/registration/password_reset_confirm.html'}, 
            name='password_reset_confirm'),
    url(r'^accounts/reset/done/$', auth_views.password_reset_complete,
            {'template_name': 'disbi/registration/password_reset_complete.html'}, 
            name='password_reset_complete'),
    url(r'^sulfolobus/', include('sulfolobus.urls')),
    url(r'^admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

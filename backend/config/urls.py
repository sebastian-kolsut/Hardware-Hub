"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from config.views import LoginView, LogoutView, MeView, UserCreateView, ping
from hardware.views import (
    HardwareDetailView,
    HardwareListView,
    HardwareRentView,
    HardwareReturnView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/ping/', ping, name='ping'),
    path('api/auth/login/', LoginView.as_view(), name='auth-login'),
    path('api/auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('api/auth/me/', MeView.as_view(), name='auth-me'),
    path('api/auth/users/', UserCreateView.as_view(), name='auth-users'),
    path('api/hardware/', HardwareListView.as_view(), name='hardware-list'),
    path('api/hardware/<int:pk>/', HardwareDetailView.as_view(), name='hardware-detail'),
    path('api/hardware/<int:pk>/rent/', HardwareRentView.as_view(), name='hardware-rent'),
    path('api/hardware/<int:pk>/return/', HardwareReturnView.as_view(), name='hardware-return'),
]

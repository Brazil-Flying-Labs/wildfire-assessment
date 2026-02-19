"""
URL configuration for api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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

from django.conf.urls import include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework import routers
from wildfire_assessment.views import (
    AIAnalysisView,
    EcologicalReserveViewSet,
    UserMeView,
    health_status,
)

router = routers.DefaultRouter()
router.register(r"ecological_reserve", EcologicalReserveViewSet)

urlpatterns = [
    path("", health_status, name="health-status"),
    path("me/", UserMeView.as_view(), name="user-me"),
    path("analysis/", AIAnalysisView.as_view(), name="ai-analysis"),
    path("", include(router.urls)),
    path(
        "admin/login/",
        auth_views.LoginView.as_view(template_name="z.html"),
        name="login",
    ),  #
    path("", include("social_django.urls", namespace="social")),
    path("admin/", admin.site.urls),
    # YOUR PATTERNS
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

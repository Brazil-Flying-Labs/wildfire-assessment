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

from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework import routers
from wildfire_assessment.admin import (
    analytics_dashboard_view,
    user_activity_report_view,
)
from wildfire_assessment.views import (
    AIAnalysisFollowUpView,
    AIAnalysisView,
    AnalysisRunViewSet,
    AreaOfInterestViewSet,
    DashboardView,
    NotificationViewSet,
    UserMeView,
    health_status,
)

router = routers.DefaultRouter()
router.register(r"area_of_interest", AreaOfInterestViewSet)
router.register(r"analysis_run", AnalysisRunViewSet, basename="analysisrun")
router.register(r"notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("", health_status, name="health-status"),
    path("me/", UserMeView.as_view(), name="user-me"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("analysis/", AIAnalysisView.as_view(), name="ai-analysis"),
    path(
        "analysis/followup/",
        AIAnalysisFollowUpView.as_view(),
        name="ai-analysis-followup",
    ),
    path("", include(router.urls)),
    path(
        "admin/login/",
        auth_views.LoginView.as_view(template_name="z.html"),
        name="login",
    ),  #
    path("", include("social_django.urls", namespace="social")),
    path(
        "admin/analytics/",
        admin.site.admin_view(analytics_dashboard_view),
        name="admin-analytics",
    ),
    path(
        "admin/user-activity/",
        admin.site.admin_view(user_activity_report_view),
        name="admin-user-activity",
    ),
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

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

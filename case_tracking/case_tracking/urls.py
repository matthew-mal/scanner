"""
URL configuration for case_tracking project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from core import views, viewsets
from core.admin import custom_admin_site
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("custom_admin/", custom_admin_site.urls),
    path("login/", views.login_view, name="login"),
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),
    path("", views.case_list, name="case_list"),
    path("manager/dashboard/", views.manager_dashboard, name="manager_dashboard"),
    path(
        "manager/assign-employee-barcode/",
        views.assign_employee_barcode,
        name="assign_employee_barcode",
    ),
    path(
        "manager/assign-stage-barcode/",
        views.assign_stage_barcode,
        name="assign_stage_barcode",
    ),
    path("employee/dashboard/", views.employee_dashboard, name="employee_dashboard"),
    path("archived_cases/", views.archived_case, name="archived_cases"),
    path("returned_cases/", views.returned_case, name="returned_cases"),
    path(
        "api/cases/scan_barcodes/",
        viewsets.CaseViewSet.as_view({"post": "scan_barcodes"}),
        name="scan_barcodes",
    ),
    path("scan-barcodes/", views.scan_barcodes_page, name="scan_barcodes_page"),
]

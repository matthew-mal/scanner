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
from core import views
from core.admin import custom_admin_site
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin_case_processing/", custom_admin_site.urls),
    path("register_case/", views.register_case, name="register_case"),
    path("update_case_stage/", views.update_case_stage, name="update_case_stage"),
    path("process_return/", views.process_return, name="process_return"),
    path("case_list/", views.case_list, name="case_list"),
    path("archived_cases/", views.archived_case, name="archived_cases"),
    path("returned_cases/", views.returned_case, name="returned_cases"),
]

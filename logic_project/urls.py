"""
URL configuration for logic_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from logic_app.views import graph_view,start_view,save_attempt_log, download_protocol,verify_view,generate_report_file,generate_protocol_file,get_protocol_content,get_report_content

urlpatterns = [
    path('admin/', admin.site.urls),
    path('graph/', graph_view, name='graph'),
    path('', start_view, name='start'),
path("save-log/", save_attempt_log, name="save_attempt_log"),
    path("download-protocol/", download_protocol, name="download_protocol"),
    path("verify/", verify_view, name="verify"),
    path('get-report-content/', get_report_content, name='get_report_content'),
path('get-protocol-content/', get_protocol_content, name='get_protocol_content'),
# path('generate-report/', generate_report_file, name='generate_report'),
#     path('generate-protocol/', generate_protocol_file, name='generate_protocol'),
]


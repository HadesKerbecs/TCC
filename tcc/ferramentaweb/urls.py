from django.urls import path
from . import views
from .views import gerar_caso_stream


urlpatterns = [
    path('', views.index, name='index'),
    path('gerar-caso-stream/', gerar_caso_stream, name='gerar_caso_stream'),
]

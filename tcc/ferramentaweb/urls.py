from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('gerar_caso/', views.gerar_caso, name='gerar_caso'),
]

from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('pegar_historico/', views.pegar_historico, name='pegar_historico'),
    path('gerar-caso-stream/', views.gerar_caso_stream, name='gerar_caso_stream'),
    path('processar_mensagem/', views.processar_mensagem, name='processar_mensagem'),
    path('personalizar-caso/', views.personalizar_caso, name='personalizar_caso'),
]

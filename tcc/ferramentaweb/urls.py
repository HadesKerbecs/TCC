from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('pegar_historico/', views.pegar_historico, name='pegar_historico'),
    path('gerar-caso-stream/', views.gerar_caso_stream, name='gerar_caso_stream'),
    path('processar_mensagem/', views.processar_mensagem, name='processar_mensagem'),
    path('personalizar-caso/', views.personalizar_caso, name='personalizar_caso'),
    path('resetar_personalizacao/', views.resetar_personalizacao, name='resetar_personalizacao'),
    path('personalizacao_dados/', views.obter_dados_personalizacao, name='personalizacao_dados'),
    path('salvar_historico/', views.salvar_historico, name='salvar_historico'),
]

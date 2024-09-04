from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('get-history/', views.get_history, name='get_history'),
    path('gerar-caso-stream/', views.gerar_caso_stream, name='gerar_caso_stream'),
    path('process-message/', views.process_message, name='process_message'),

]

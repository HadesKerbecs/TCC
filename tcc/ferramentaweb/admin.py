from django.contrib import admin
from .models import Historico_Conversa, Historico_Conversa_Transferida

@admin.register(Historico_Conversa)
class HistoricoConversaAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'timestamp', 'message', 'response', 'nivel_complexidade')

@admin.register(Historico_Conversa_Transferida)
class HistoricoTransferidoAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'timestamp', 'message', 'response', 'nivel_complexidade')
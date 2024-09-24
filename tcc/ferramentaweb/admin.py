from django.contrib import admin
from .models import Historico_Conversa

@admin.register(Historico_Conversa)
class HistoricoConversaAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'timestamp', 'message', 'response', 'nivel_complexidade')
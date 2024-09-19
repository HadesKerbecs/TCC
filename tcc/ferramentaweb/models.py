# models.py
from django.db import models

class Historico_Conversa(models.Model):
    user_id = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)  # Data e hora da mensagem
    message = models.TextField()  # Mensagem do usuário
    response = models.TextField()

    def __str__(self):
        return f"Message from {self.user_id} at {self.timestamp}"

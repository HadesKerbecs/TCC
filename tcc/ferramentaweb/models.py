# models.py
from django.db import models

class ConversationHistory(models.Model):
    user_id = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField()  # Mensagem do usuário
    timestamp = models.DateTimeField(auto_now_add=True)  # Data e hora da mensagem

    def __str__(self):
        return f"Message from {self.user_id} at {self.timestamp}"

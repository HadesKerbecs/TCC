from django.db import models

class Historico_Conversa(models.Model):
    user_id = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    response = models.TextField()
    nivel_complexidade = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"Message from {self.user_id} at {self.timestamp}"

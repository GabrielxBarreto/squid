from django.db import models

class Streaming(models.Model):
    nome = models.CharField(max_length=100)
    preco_total = models.DecimalField(max_digits=8, decimal_places=2)
    max_membros = models.PositiveIntegerField()
    descricao = models.TextField(blank=True)

    def preco_por_membro(self):
        return self.preco_total / self.max_membros

    def __str__(self):
        return self.nome
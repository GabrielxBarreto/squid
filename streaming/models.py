from django.db import models

class Streaming(models.Model):
    nome = models.CharField(max_length=50) # Nome do serviço de streaming
    preco_total = models.DecimalField(max_digits=6, decimal_places=2) # Preço total do plano de streaming, posteriormente dividido pelos membros
    max_membros = models.PositiveIntegerField() # Número maximo de membros permitido em um mesmo plano de streaming
    descricao = models.TextField(blank=True) # Descrição (opcional) do serviço de streaming

    def preco_por_membro(self):
        return round(self.preco_total / self.max_membros, 2) # Calculo do preço por membro usando 'max_membros' com divisão por 'preço_total'

    def preco_dono(self): # Resolve o dilema da divisão de valores, fazendo o dono do grupo assumir a diferença
        valor_membro = round(self.preco_total / self.max_membros, 2) # preco_por_membro
        total_coberto = valor_membro * (self.max_membros - 1) # Total que os membros pagam juntos tirando um 'membro'
        return round(self.preco_total - total_cobrado, 2) # Preço que todos os membros pagam - valor total, assim o dono paga os centavos de arredondamento


    def __str__(self):
        return self.nome # Retorna o nome do serviço de streaming quando objeto for chamado na interface
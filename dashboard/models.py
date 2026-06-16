from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.
class User(models.Model):
    #o jeito Django de classes abstratas 
    username = models.CharField(max_length=45)
    email = models.EmailField()
    senha = models.CharField(max_length=128)

    
    class Meta:
        abstract = True
    def deletar_conta(self):
        self.delete()
        
class Streaming(models.Model):
    name = models.CharField(max_length=45)
    url = models.CharField(max_length=255,default="https://teste.com")
    categoria = models.CharField(max_length=128,default="Video")

    def __str__(self):
        return self.name
    
class Plano(models.Model):
    name = models.CharField(max_length=45)
    preco_mensal = models.FloatField()
    qualidade_video = models.CharField(max_length=30)
    ativo = models.BooleanField()
    quantidade_telas = models.IntegerField()
    anuncio = models.BooleanField()
    #Barreto: adicionei a forgein key para o streaming, pois cada plano pertence a um streaming específico
    streaming = models.ForeignKey(Streaming, on_delete=models.CASCADE, default=1, null = True,blank=True)

class Participante(AbstractUser):
    data_cadastro= models.DateField(auto_now_add=True)
    status = models.BooleanField(default=True) 
    def __str__(self):
            return self.username

class Grupo(models.Model):
    owner = models.ForeignKey(Participante, on_delete=models.CASCADE, related_name="meus_grupos")
    name = models.CharField(max_length=45)
    descricao = models.CharField(max_length=255, blank=True, null=True)
    plano = models.ForeignKey(Plano, on_delete=models.CASCADE)
    streaming = models.ForeignKey(Streaming, on_delete=models.CASCADE)
    dia_vencimento = models.IntegerField(default=15) # Novo: Dia do mês que a conta vence
    cobranca_automatica = models.BooleanField(default=True) # Novo: Toggle do app
    streak_pagamentos = models.PositiveIntegerField(default=0)
    assinatura_paga = models.BooleanField(default=False)
    # Novo: Relação de quem faz parte do grupo para dividir a conta
    membros = models.ManyToManyField(Participante, through='MembroGrupo', related_name="grupos_participo")

    def __str__(self):
        return self.name

# Novo: Tabela intermédia para gerir se o amigo já pagou este mês
class MembroGrupo(models.Model):
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE)
    participante = models.ForeignKey(Participante, on_delete=models.CASCADE)
    status_pagamento = models.BooleanField(default=False) # False = Pendente/Devendo, True = Pago
    streak = models.PositiveIntegerField(default=0)
    @property
    def valor_devido(self):
        # Divide o valor total pelo número de membros + o dono
        total_pessoas = self.grupo.membros.count() + 1 
        return self.grupo.plano.preco_mensal / total_pessoas
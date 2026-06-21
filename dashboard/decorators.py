from django.utils import timezone
from django.core.mail import send_mail
from .models import Grupo, MembroGrupo

def verificar_e_enviar_cobrancas(view_func):
    def wrapper(request, *args, **kwargs):
        # 1. Pega o dia atual
        hoje = timezone.now().day
        
        # 2. Busca grupos que vencem hoje
        grupos_vencendo = Grupo.objects.filter(dia_vencimento=hoje)
        
        for grupo in grupos_vencendo:
            # 3. Busca membros deste grupo específico
            membros = MembroGrupo.objects.filter(grupo=grupo, status_pagamento=False)
            
            for membro in membros:
                try:
                    send_mail(
                        'Cobrança de Streaming - Vencimento Hoje',
                        f'Olá {membro.participante.username}, o pagamento do grupo {grupo.name} venceu hoje. Valor: R$ {membro.valor_devido:.2f}.',
                        'corpaligatorl@gmail.com',
                        [membro.participante.email],
                        fail_silently=False,
                    )
                    # Opcional: Marcar algum log ou flag de "notificado" se quiser
                except Exception as e:
                    print(f"Erro ao enviar para {membro.participante.email}: {e}")
        
        return view_func(request, *args, **kwargs)
    return wrapper
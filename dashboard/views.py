from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings

from dashboard import models


from django.shortcuts import render
from .decorators import verificar_e_enviar_cobrancas

# ==================== PÁGINAS PÚBLICAS E AUTENTICAÇÃO ====================

def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')

def login_view(request):
    if request.method == 'POST':
        nome_digitado = request.POST.get('nome')
        senha_digitada = request.POST.get('senha')

        user = authenticate(request, username=nome_digitado, password=senha_digitada)

        if user is not None:
            django_login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'E-mail ou senha incorretos.')
            
    return render(request, 'login.html')
    
def cadastro_view(request):
    if request.method == 'POST':
        name = request.POST.get("nome")
        email = request.POST.get("email")
        senha = request.POST.get("senha")
        
        # Validação simples
        if models.Participante.objects.filter(username=name).exists():
            messages.error(request, 'Nome de usuário já existe.')
            return render(request, 'cadastro.html')

        user = models.Participante.objects.create_user(
            username=name, 
            email=email,
            password=senha 
        )
        user.save()
        messages.success(request, 'Conta criada com sucesso! Faça login.')
        return redirect("login")
        
    return render(request, 'cadastro.html')

def logout_view(request):
    django_logout(request)
    return redirect('index')

def carregar_planos(request):
    streaming_id = request.GET.get('streaming_id')
    # Filtra os planos onde a chave estrangeira do streaming bate com o ID enviado
    planos = models.Plano.objects.filter(streaming_id=streaming_id).values('id', 'name')
    return JsonResponse(list(planos), safe=False)

# ==================== ÁREA LOGADA ====================


@login_required(login_url='/login/')
@verificar_e_enviar_cobrancas
def dashboard(request):
    usuario = request.user
    meus_grupos = models.Grupo.objects.filter(owner=usuario)
    vincos_participante = models.MembroGrupo.objects.filter(participante=usuario)
    grupos_participando = []

    for vinculo in vincos_participante:
        grupo_alheio = vinculo.grupo
        membros_desse_grupo = models.MembroGrupo.objects.filter(grupo=grupo_alheio)
        total_pessoas = membros_desse_grupo.count() + 1 # Membros + Dono
        
        valor_plano = grupo_alheio.plano.preco_mensal
        minha_parte = valor_plano / total_pessoas
        
        grupos_participando.append({
            'nome_streaming': grupo_alheio.streaming.name,
            'dono': grupo_alheio.owner.username,
            'dia_vencimento': grupo_alheio.dia_vencimento,
            'minha_parte': f"{minha_parte:.2f}".replace('.', ','),
            'status_pagamento': vinculo.status_pagamento,
            'ocultar_membros': grupo_alheio.ocultar_membros,
            'membros': membros_desse_grupo
        })

    # Cálculos Financeiros
    gasto_total = 0
    economia_total = 0
    proximos_vencimentos = []
    amigos_pendentes = []

    for grupo in meus_grupos:
        valor_plano = grupo.plano.preco_mensal

        membros_grupo = models.MembroGrupo.objects.filter(grupo=grupo)

        total_pessoas = grupo.membros.count() + 1 # Membros + Dono
        
        # Quanto o dono realmente paga
        meu_gasto_real = valor_plano / total_pessoas
        gasto_total += meu_gasto_real
        
        # Quanto o dono economiza por dividir
        economia_total += (valor_plano - meu_gasto_real)
        
        

        proximos_vencimentos.append({
            'id': grupo.id,
            'nome': grupo.streaming.name,
            'dia': grupo.dia_vencimento,
            'valor_total': valor_plano,
            'cobranca_automatica': grupo.cobranca_automatica,
            'pendentes_count': membros_grupo.filter(status_pagamento=False).count(),
            'link_convite': request.build_absolute_uri(f"/grupo/entrar/{grupo.id}/"),
            'membros': membros_grupo,
            'streak_pagamentos': grupo.streak_pagamentos,
})
        
        # Buscar amigos que estão a dever neste grupo
        devedores = models.MembroGrupo.objects.filter(grupo=grupo, status_pagamento=False)
        for devedor in devedores:
            amigos_pendentes.append({
                'nome': devedor.participante.username,
                'servico': grupo.streaming.name,
                'valor': devedor.valor_devido
            })

    context = {
        'gasto_total': f"{gasto_total:.2f}".replace('.', ','),
        'economia_total': f"{economia_total:.2f}".replace('.', ','),
        'vencimentos': proximos_vencimentos,
        'pendentes': amigos_pendentes,
        'grupos_participando' : grupos_participando,
        'streamings': models.Streaming.objects.all(),
        'planos': models.Plano.objects.all(),
    }
    
    return render(request, 'dashboard.html', context)








    




@login_required(login_url='/login/') # A trava de segurança que comentei antes!
def cobrarAmigo(request, email):
    assunto = 'Lembrete de pagamento - Cobrança Individual'
    mensagem = 'Verifique sua parte da assinatura do grupo que está pendente. Acesse o App para regularizar seu pagamento.'
    
    if email:
        # Usa o .delay() para enviar a tarefa para o Celery em background
        send_mail(
        subject=assunto,
        message=mensagem,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        fail_silently=False,
    )
        
        # A página carrega na hora, sem esperar o e-mail ser de fato enviado
        messages.success(request, f"A cobrança para {email} foi adicionada à fila de envio!")
    else:
        messages.error(request, "Não foi possível enviar a cobrança: e-mail inválido.")
    
    return redirect('dashboard')

@login_required(login_url='/login/')
def criarGrupo(request):
    if request.method == 'POST':
        ocultar_membros = request.POST.get('ocultar_membros') == 'on'
        grupo = models.Grupo.objects.create(
            owner=request.user, # Pega o usuário logado com segurança
            name=request.POST.get('name'),
            descricao=request.POST.get('descricao'),
            plano_id=request.POST.get('plano'),
            streaming_id=request.POST.get('streaming'),
            dia_vencimento = request.POST.get('dia_vencimento'),
            ocultar_membros=ocultar_membros
        )
        
        grupo.save()
        
    return redirect("dashboard")


@login_required(login_url='/login/')
def excluirGrupo(request, grupo_id):
    grupo = get_object_or_404(models.Grupo, id=grupo_id)
    if request.method == 'GET':
        grupo.delete()
    return redirect("dashboard")
            
@login_required(login_url='/login/')
def entrar_grupo(request, grupo_id):
    grupo = get_object_or_404(models.Grupo, id=grupo_id)
    
    # 1. Se o dono clicar no próprio link, não faz sentido ele entrar como membro
    if grupo.owner == request.user:
        messages.warning(request, "Você é o dono deste grupo!")
        return redirect('dashboard')
        
    # 2. Verificar se o usuário já está no grupo para não duplicar
    if models.MembroGrupo.objects.filter(grupo=grupo, participante=request.user).exists():
        messages.info(request, "Você já faz parte deste grupo!")
        return redirect('dashboard')
        
    # 3. Adiciona o participante usando a tabela intermediária que você criou
    models.MembroGrupo.objects.create(grupo=grupo, participante=request.user)
    messages.success(request, f"Boa! Você entrou no grupo {grupo.name}.")
    
    return redirect('dashboard')

@login_required(login_url='/login/')
def detalhe_membro(request, membro_id):
    # Pega o registro do membro associado ao grupo
    membro_grupo = get_object_or_404(models.MembroGrupo, id=membro_id)
    grupo = membro_grupo.grupo
    
    # Segurança: Apenas o dono do grupo pode ver esse perfil individual
    if grupo.owner != request.user:
        messages.error(request, "Você não tem permissão para visualizar este perfil.")
        return redirect('dashboard')
        
    context = {
        'membro': membro_grupo.participante,
        'vinculo': membro_grupo,
        'grupo': grupo
    }
    return render(request, 'perfil_membro.html', context)


@login_required(login_url='/login/')
def detalhe_grupo(request, grupo_id):
    grupo = get_object_or_404(models.Grupo, id=grupo_id)
    membros = models.MembroGrupo.objects.filter(grupo=grupo)

    usuario_eh_dono = grupo.owner == request.user
    vinculo_usuario = membros.filter(participante=request.user).first()
    usuario_eh_membro = vinculo_usuario is not None

    if not usuario_eh_dono and not usuario_eh_membro:
        messages.error(request, "Você não tem permissão para acessar este grupo.")
        return redirect('dashboard')

    total_membros = membros.count()
    total_pessoas = total_membros + 1
    valor_por_pessoa = grupo.plano.preco_mensal / total_pessoas

    membros_pagos = membros.filter(status_pagamento=True).count()
    membros_pendentes = membros.filter(status_pagamento=False).count()

    context = {
        'grupo': grupo,
        'membros': membros,
        'usuario_eh_dono': usuario_eh_dono,
        'usuario_eh_membro': usuario_eh_membro,
        'vinculo_usuario': vinculo_usuario,
        'valor_por_pessoa': valor_por_pessoa,
        'total_pessoas': total_pessoas,
        'membros_pagos': membros_pagos,
        'membros_pendentes': membros_pendentes,

        'link_convite': request.build_absolute_uri(
        f"/grupo/entrar/{grupo.id}/"
    ),
    }

    return render(request, 'detalhe_grupo.html', context)
# ==================== API / CRUD RÁPIDO ====================     

@login_required(login_url='/login/')

def cobrar_participantes(request, grupo_id):
    grupo = get_object_or_404(models.Grupo, id=grupo_id)

    if grupo.owner != request.user:
        messages.error(request, "Você não tem permissão para cobrar participantes deste grupo.")
        return redirect('dashboard')

    membros_pendentes = models.MembroGrupo.objects.filter(
        grupo=grupo,
        status_pagamento=False
    )

    enviados = 0
    sem_email = 0

    for membro in membros_pendentes:
        email = membro.participante.email

        if email:
            try:
                send_mail(
                    subject=f'Lembrete de pagamento - {grupo.streaming.name}',
                    message=(
                        f'Olá, {membro.participante.username}.\n\n'
                        f'Sua parte da assinatura do grupo "{grupo.name}" ainda está pendente.\n'
                        f'Valor aproximado: R$ {membro.valor_devido:.2f}.\n\n'
                        f'Acesse o SubSplit para regularizar seu pagamento.'
                    ),
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[email],
                    fail_silently=False,
                )
                enviados += 1
            except Exception as e:
                messages.error(request, f"Erro ao enviar para {email}: {e}")
        else:
            sem_email += 1

    messages.success(
        request,
        f"Cobrança enviada para {enviados} participante(s). {sem_email} participante(s) sem email."
    )

    return redirect('detalhe_grupo', grupo_id=grupo.id)

def listUsers(request):
    users = list(models.Participante.objects.values('id', 'username', 'email'))
    return JsonResponse({'users': users})

def updateUser(request, id):
    user = get_object_or_404(models.Participante, id=id) 
    if request.method == 'POST':
        user.username = request.POST.get("name")
        user.email = request.POST.get("email")
        user.save()
        return redirect("index")

def deleteUser(request, id):
    user = get_object_or_404(models.Participante, id=id) 
    user.delete()
    return redirect("index")

@login_required(login_url='/login/')
def marcar_pagamento(request, membro_id):
    membro = get_object_or_404(models.MembroGrupo, id=membro_id)

    if not membro.status_pagamento:
        membro.status_pagamento = True
        membro.save()

    grupo = membro.grupo

    todos_pagaram = not models.MembroGrupo.objects.filter(
        grupo=grupo,
        status_pagamento=False
    ).exists()

    if todos_pagaram and not grupo.assinatura_paga:
        grupo.assinatura_paga = True
        grupo.streak_pagamentos += 1
        grupo.save()

    return redirect('dashboard')

@login_required(login_url='/login/')
def desfazer_pagamento(request, membro_id):
    membro = get_object_or_404(models.MembroGrupo, id=membro_id)
    grupo = membro.grupo

    if membro.status_pagamento:
        membro.status_pagamento = False
        membro.save()

        grupo.assinatura_paga = False
        
        if grupo.streak_pagamentos > 0:
            grupo.streak_pagamentos -= 1
            
        grupo.save()
    return redirect('dashboard')

@login_required(login_url='/login/')
def alternar_pagamento(request, membro_id):
    membro = get_object_or_404(models.MembroGrupo, id=membro_id)
    grupo = membro.grupo
    estava_pago = membro.status_pagamento
    membro.status_pagamento = not membro.status_pagamento
    membro.save()
    if not estava_pago:
        todos_pagaram = not models.MembroGrupo.objects.filter(
            grupo=grupo,
            status_pagamento=False
        ).exists()
        if todos_pagaram and not grupo.assinatura_paga:
            grupo.assinatura_paga = True
            grupo.streak_pagamentos += 1
    else:
        grupo.assinatura_paga = False
        if grupo.streak_pagamentos > 0:
            grupo.streak_pagamentos -= 1
    grupo.save()
    return redirect('detalhe_grupo', grupo_id=grupo.id)

@login_required(login_url='/login/')
def remover_membro(request, membro_id):
    membro_grupo = get_object_or_404(models.MembroGrupo, id=membro_id)

    # Segurança: Garante que apenas o OWNER do grupo pode remover alguém
    if membro_grupo.grupo.owner != request.user:
        messages.error(request, "Você não tem permissão para remover este participante.")
        return redirect('dashboard')
    
    # Guarda o nome antes de deletar para exibir na mensagem
    nome_usuario = membro_grupo.participante.username
    nome_streaming = membro_grupo.grupo.streaming.name

    # Remove o participante do grupo
    membro_grupo.delete()
    
    messages.success(request, f"{nome_usuario} foi removido do grupo do {nome_streaming}.")
    return redirect('dashboard')
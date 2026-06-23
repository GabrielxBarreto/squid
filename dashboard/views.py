from abc import ABC, abstractmethod
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from dashboard import models

# =========================================================================
# PADRÃO 1: OBSERVER (NOTIFICAÇÕES E COBRANÇAS DESACOPLADAS)
# =========================================================================

class NotificationObserver(ABC):
    @abstractmethod
    def update(self, event_type, context):
        pass

class EmailBillingObserver(NotificationObserver):
    """Observer responsável por disparar e-mails do sistema."""
    def update(self, event_type, context):
        if event_type == 'cobrar_unico':
            email = context.get('email')
            send_mail(
                subject='Lembrete de pagamento',
                message='Sua parte da assinatura está pendente. Acesse o App!',
                html_message='<p>Sua parte da assinatura está pendente. Acesse o App!</p>',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        elif event_type == 'cobrar_lista':
            membro = context.get('membro')
            grupo = context.get('grupo')
            send_mail(
                subject=f'Lembrete de pagamento - {grupo.streaming.name}',
                message=(
                    f'Olá, {membro.participante.username}.\n\n'
                    f'Sua parte da assinatura do grupo "{grupo.name}" ainda está pendente.\n'
                    f'Valor aproximado: R$ {membro.valor_devido:.2f}.\n\n'
                    f'Acesse o SubSplit para regularizar seu pagamento.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[membro.participante.email],
                fail_silently=True,
            )

class BillingPublisher:
    """Sujeito que armazena e notifica observadores cadastrados."""
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def notify(self, event_type, context):
        for observer in self._observers:
            observer.update(event_type, context)

# Inicialização global do Publisher e registro do Observer de Email
billing_publisher = BillingPublisher()
billing_publisher.attach(EmailBillingObserver())


# =========================================================================
# PADRÃO 2: FACTORY METHOD (CUSTOMIZAÇÃO POR PLATAFORMA)
# =========================================================================

class StreamingFactory(ABC):
    @abstractmethod
    def configurar_assinatura(self, grupo, plano):
        pass

class NetflixFactory(StreamingFactory):
    def configurar_assinatura(self, grupo, plano):
        grupo.descricao = f"[Netflix - {plano.name}] {grupo.descricao or ''}".strip()
        return grupo

class SpotifyFactory(StreamingFactory):
    def configurar_assinatura(self, grupo, plano):
        grupo.descricao = f"[Spotify Família - {plano.name}] {grupo.descricao or ''}".strip()
        return grupo

class GenericStreamingFactory(StreamingFactory):
    def configurar_assinatura(self, grupo, plano):
        return grupo

class StreamingFactoryProvider:
    @staticmethod
    def get_factory(streaming_name):
        name_lower = streaming_name.lower()
        if 'netflix' in name_lower:
            return NetflixFactory()
        elif 'spotify' in name_lower:
            return SpotifyFactory()
        return GenericStreamingFactory()


# =========================================================================
# PADRÃO 3: FACADE (FACHADA UNIFICADA DE CRIAÇÃO)
# =========================================================================

class AssinaturaFacade:
    @staticmethod
    def criar_assinatura_compartilhada(user, data):
        plano_id = data.get('plano')
        streaming_id = data.get('streaming')
        name = data.get('name')
        descricao = data.get('descricao')
        dia_vencimento = data.get('dia_vencimento')
        ocultar_membros = data.get('ocultar_membros') == 'on'

        plano = models.Plano.objects.get(id=plano_id)
        streaming = models.Streaming.objects.get(id=streaming_id)

        # Criação da entidade básica
        grupo = models.Grupo(
            owner=user,
            name=name,
            descricao=descricao,
            plano=plano,
            streaming=streaming,
            dia_vencimento=dia_vencimento,
            ocultar_membros=ocultar_membros
        )

        # Execução das regras específicas do Factory Method escolhido
        factory = StreamingFactoryProvider.get_factory(streaming.name)
        grupo = factory.configurar_assinatura(grupo, plano)
        
        grupo.save()
        return grupo


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
            messages.error(request, 'Usuário ou senha incorretos.')
            
    return render(request, 'login.html')
    
def cadastro_view(request):
    if request.method == 'POST':
        name = request.POST.get("nome")
        email = request.POST.get("email")
        senha = request.POST.get("senha")
        
        if models.Participante.objects.filter(username=name).exists():
            messages.error(request, 'Nome de usuário já existe.')
            return render(request, 'cadastro.html')

        user = models.Participante.objects.create_user(
            username=name, 
            email=email,
            password=senha 
        )
        user.save()
        messages.success(request, 'Conta criada com sucesso!')
        return redirect("login")
        
    return render(request, 'cadastro.html')

def logout_view(request):
    django_logout(request)
    return redirect('index')

def carregar_planos(request):
    streaming_id = request.GET.get('streaming_id')
    planos = models.Plano.objects.filter(streaming_id=streaming_id).values('id', 'name')
    return JsonResponse(list(planos), safe=False)


# ==================== ÁREA LOGADA ====================

@login_required(login_url='/login/')
def dashboard(request):
    usuario = request.user
    meus_grupos = models.Grupo.objects.filter(owner=usuario)
    vincos_participante = models.MembroGrupo.objects.filter(participante=usuario)
    grupos_participando = []

    for vinculo in vincos_participante:
        grupo_alheio = vinculo.grupo
        membros_desse_grupo = models.MembroGrupo.objects.filter(grupo=grupo_alheio)
        total_pessoas = membros_desse_grupo.count() + 1 
        
        valor_plano = grupo_alheio.plano.preco_mensal
        minha_parte = valor_plano / total_pessoas
        
        grupos_participando.append({
            'id': grupo_alheio.id,
            'nome_grupo': grupo_alheio.name,
            'nome_streaming': grupo_alheio.streaming.name,
            'dono': grupo_alheio.owner.username,
            'dia_vencimento': grupo_alheio.dia_vencimento,
            'minha_parte': f"{minha_parte:.2f}".replace('.', ','),
            'status_pagamento': vinculo.status_pagamento,
            'ocultar_membros': grupo_alheio.ocultar_membros,
            'membros': membros_desse_grupo,
            'streak_pagamentos': grupo_alheio.streak_pagamentos,
        })

    gasto_total = 0
    economia_total = 0
    proximos_vencimentos = []
    amigos_pendentes = []

    for grupo in meus_grupos:
        valor_plano = grupo.plano.preco_mensal
        membros_grupo = models.MembroGrupo.objects.filter(grupo=grupo)
        total_pessoas = grupo.membros.count() + 1 
        
        meu_gasto_real = valor_plano / total_pessoas
        gasto_total += meu_gasto_real
        economia_total += (valor_plano - meu_gasto_real)

        proximos_vencimentos.append({
            'id': grupo.id,
            'nome_grupo': grupo.name,
            'nome': grupo.streaming.name,
            'dia': grupo.dia_vencimento,
            'valor_total': valor_plano,
            'cobranca_automatica': grupo.cobranca_automatica,
            'pendentes_count': membros_grupo.filter(status_pagamento=False).count(),
            'link_convite': request.build_absolute_uri(f"/grupo/entrar/{grupo.id}/"),
            'membros': membros_grupo,
            'streak_pagamentos': grupo.streak_pagamentos,
        })
        
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
        'grupos_participando': grupos_participando,
        'streamings': models.Streaming.objects.all(),
        'planos': models.Plano.objects.all(),
    }
    return render(request, 'dashboard.html', context)


@login_required(login_url='/login/')
def cobrarAmigo(request, grupo_id, email):
    if email:
        try:
            # Uso do padrão Observer para disparar a ação de envio
            billing_publisher.notify('cobrar_unico', {'email': email})
            messages.success(request, f"E-mail enviado para {email} via Resend.")
        except Exception as e:
            messages.error(request, f"Erro ao enviar e-mail: {e}")
    return redirect('detalhe_grupo', grupo_id=grupo_id)


@login_required(login_url='/login/')
def criarGrupo(request):
    if request.method == 'POST':
        try:
            # Uso do padrão Facade para unificar e encapsular a criação
            AssinaturaFacade.criar_assinatura_compartilhada(request.user, request.POST)
            messages.success(request, "Grupo de assinatura criado com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao criar o grupo de assinatura: {e}")
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
    
    if grupo.owner == request.user:
        messages.warning(request, "Você é o dono deste grupo!")
        return redirect('dashboard')
        
    if models.MembroGrupo.objects.filter(grupo=grupo, participante=request.user).exists():
        messages.info(request, "Você já faz parte deste grupo!")
        return redirect('dashboard')
        
    models.MembroGrupo.objects.create(grupo=grupo, participante=request.user)
    messages.success(request, f"Boa! Você entrou no grupo {grupo.name}.")
    return redirect('dashboard')

@login_required(login_url='/login/')
def detalhe_membro(request, membro_id):
    membro_grupo = get_object_or_404(models.MembroGrupo, id=membro_id)
    grupo = membro_grupo.grupo
    
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
        'link_convite': request.build_absolute_uri(f"/grupo/entrar/{grupo.id}/"),
    }
    return render(request, 'detalhe_grupo.html', context)


@login_required(login_url='/login/')
def cobrar_participantes(request, grupo_id):
    grupo = get_object_or_404(models.Grupo, id=grupo_id)

    if grupo.owner != request.user:
        messages.error(request, "Você não tem permissão para cobrar participantes deste grupo.")
        return redirect('dashboard')

    membros_pendentes = models.MembroGrupo.objects.filter(grupo=grupo, status_pagamento=False)
    enviados = 0
    sem_email = 0

    for membro in membros_pendentes:
        if membro.participante.email:
            try:
                # Uso do padrão Observer substituindo a chamada direta de envio de e-mail local
                billing_publisher.notify('cobrar_lista', {'membro': membro, 'grupo': grupo})
                enviados += 1
            except Exception as e:
                messages.error(request, f"Erro ao enviar para {membro.participante.email}: {e}")
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
    todos_pagaram = not models.MembroGrupo.objects.filter(grupo=grupo, status_pagamento=False).exists()

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
    if grupo.owner != request.user:
        messages.error(request, "Você não tem permissão para alterar pagamentos.")
        return redirect('dashboard')
        
    estava_pago = membro.status_pagamento
    membro.status_pagamento = not membro.status_pagamento
    membro.save()
    
    if not estava_pago:
        todos_pagaram = not models.MembroGrupo.objects.filter(grupo=grupo, status_pagamento=False).exists()
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
def alternar_ocultar_membros(request, grupo_id):
    grupo = get_object_or_404(models.Grupo, id=grupo_id)

    if grupo.owner != request.user:
        messages.error(request, "Você não tem permissão para alterar este grupo.")
        return redirect('dashboard')

    grupo.ocultar_membros = not grupo.ocultar_membros
    grupo.save()

    return redirect('detalhe_grupo', grupo_id=grupo.id)

@login_required(login_url='/login/')
def remover_membro(request, membro_id):
    membro_grupo = get_object_or_404(models.MembroGrupo, id=membro_id)

    if membro_grupo.grupo.owner != request.user:
        messages.error(request, "Você não tem permissão para remover este participante.")
        return redirect('dashboard')
    
    nome_usuario = membro_grupo.participante.username
    nome_streaming = membro_grupo.grupo.streaming.name
    membro_grupo.delete()
    
    messages.success(request, f"{nome_usuario} foi removido do grupo do {nome_streaming}.")
    return redirect('dashboard')

@login_required(login_url='/login/')
def sair_grupo(request, grupo_id):
    vinculo = get_object_or_404(models.MembroGrupo, grupo_id=grupo_id, participante=request.user)
    vinculo.delete()
    messages.success(request, f"Você saiu do grupo {vinculo.grupo.name}.")
    return redirect('dashboard')
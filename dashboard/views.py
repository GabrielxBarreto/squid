from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from dashboard import models

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

# ==================== ÁREA LOGADA ====================

@login_required(login_url='/login/')
def dashboard(request):
    usuario = request.user
    meus_grupos = models.Grupo.objects.filter(owner=usuario)
    
    # Cálculos Financeiros
    gasto_total = 0
    economia_total = 0
    proximos_vencimentos = []
    amigos_pendentes = []

    for grupo in meus_grupos:
        valor_plano = grupo.plano.preco_mensal
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
            'pendentes_count': grupo.membros.filter(membrogrupo__status_pagamento=False).count(),
            'link_convite': request.build_absolute_uri(f"/grupo/entrar/{grupo.id}/")
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
        'streamings': models.Streaming.objects.all(),
        'planos': models.Plano.objects.all(),
    }
    
    return render(request, 'dashboard.html', context)
@login_required(login_url='/login/')
def criarGrupo(request):
    if request.method == 'POST':
        grupo = models.Grupo.objects.create(
            owner=request.user, # Pega o usuário logado com segurança
            name=request.POST.get('name'),
            descricao=request.POST.get('descricao'),
            plano_id=request.POST.get('plano'),
            streaming_id=request.POST.get('streaming')
        )
        grupo.save()
    return redirect("dashboard")

@login_required(login_url='/login/')
def entrar_grupo(request, grupo_id):
    grupo = get_object_or_404(models.Grupo, id=grupo_id)
    
    # 1. Se o dono clicar no próprio link, não faz sentido ele entrar como membro
    if grupo.owner == request.user:
        messages.warning(request, "Você é o dono deste grupo!")
        return redirect('dashboard')
        
    # 2. Verificar se o usuário já está no grupo para não duplicar
    if grupo.membros.filter(id=request.user.id).exists():
        messages.info(request, "Você já faz parte deste grupo!")
        return redirect('dashboard')
        
    # 3. Adiciona o participante usando a tabela intermediária que você criou
    models.MembroGrupo.objects.create(grupo=grupo, participante=request.user)
    messages.success(request, f"Boa! Você entrou no grupo {grupo.name}.")
    
    return redirect('dashboard')

# ==================== API / CRUD RÁPIDO ====================

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
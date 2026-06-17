from django.urls import path
from dashboard import views

urlpatterns = [
    # Telas Principais
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/cobrarAmigo/<str:email>/', views.cobrar_amigo, name='cobrarAmigo'),

    
    # Área Logada
    path('dashboard/', views.dashboard, name='dashboard'),
    path('criarGrupo/', views.criarGrupo, name='criarGrupo'),
    #carregando os planos em tempo real com AJAX
    path('ajax/carregar-planos/', views.carregar_planos, name='ajax_carregar_planos'),
    # No seu urls.py, adicione essa linha junto com as outras:
    path('grupo/entrar/<int:grupo_id>/', views.entrar_grupo, name='entrar_grupo'),
    
    path('pagamento/<int:membro_id>/', views.marcar_pagamento, name='marcar_pagamento' ),     
    path('desfazer-pagamento/<int:membro_id>/', views.desfazer_pagamento, name='desfazer_pagamento'),
    
    path('membro/<int:membro_id>/', views.detalhe_membro, name='detalhe_membro'),
    path('membro/<int:membro_id>/remover/', views.remover_membro, name='remover_membro'),
    # APIs e Testes
    path('api/users/', views.listUsers, name='api_users'),
    path('api/users/updateUser/<int:id>/', views.updateUser, name='updateUser'),
    path('api/users/deleteUser/<int:id>/', views.deleteUser, name='deleteUser'),
    
]
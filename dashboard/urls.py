from django.urls import path
from dashboard import views

urlpatterns = [
    # Telas Principais
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/cobrarAmigo/<int:grupo_id>/<str:email>/', views.cobrarAmigo, name='cobrarAmigo'),
    
    path('grupo/<int:grupo_id>/cobrar_participantes/', views.cobrar_participantes, name='cobrar_participantes' ),
    
    # Área Logada
    path('dashboard/', views.dashboard, name='dashboard'),
    path('criarGrupo/', views.criarGrupo, name='criarGrupo'),
    #carregando os planos em tempo real com AJAX
    path('ajax/carregar-planos/', views.carregar_planos, name='ajax_carregar_planos'),

    #gerenciamento de grupos
    path('grupo/entrar/<int:grupo_id>/', views.entrar_grupo, name='entrar_grupo'),
    path('grupo/<int:grupo_id>/', views.detalhe_grupo, name='detalhe_grupo'),
    path('excluirGrupo/<int:grupo_id>/', views.excluirGrupo, name='excluirGrupo'),
    path('pagamento/<int:membro_id>/', views.marcar_pagamento, name='marcar_pagamento' ),     
    path('desfazer-pagamento/<int:membro_id>/', views.desfazer_pagamento, name='desfazer_pagamento'),
    path('pagamento/alternar/<int:membro_id>/', views.alternar_pagamento, name='alternar_pagamento'),
    path('grupo/sair/<int:grupo_id>/', views.sair_grupo, name='sair_grupo'),
    path('membro/<int:membro_id>/', views.detalhe_membro, name='detalhe_membro'),
    path('membro/<int:membro_id>/remover/', views.remover_membro, name='remover_membro'),
    path('grupo/<int:grupo_id>/ocultar-membros/', views.alternar_ocultar_membros, name='alternar_ocultar_membros'),
    # APIs e Testes
    path('api/users/', views.listUsers, name='api_users'),
    path('api/users/updateUser/<int:id>/', views.updateUser, name='updateUser'),
    path('api/users/deleteUser/<int:id>/', views.deleteUser, name='deleteUser'),
    
]
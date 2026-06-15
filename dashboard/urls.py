from django.urls import path
from dashboard import views

urlpatterns = [
    # Telas Principais
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('logout/', views.logout_view, name='logout'),
    
    # Área Logada
    path('dashboard/', views.dashboard, name='dashboard'),
    path('criarGrupo/', views.criarGrupo, name='criarGrupo'),
    # No seu urls.py, adicione essa linha junto com as outras:
    path('grupo/entrar/<int:grupo_id>/', views.entrar_grupo, name='entrar_grupo'),

    # APIs e Testes
    path('api/users/', views.listUsers, name='api_users'),
    path('api/users/updateUser/<int:id>/', views.updateUser, name='updateUser'),
    path('api/users/deleteUser/<int:id>/', views.deleteUser, name='deleteUser'),
    
]
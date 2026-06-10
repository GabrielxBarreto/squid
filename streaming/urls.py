from django.urls import path
from . import views

app_name = 'streaming'

urlpatterns = [
    path('', views.StreamingListView.as_view(), name='lista'),
    path('novo/', views.StreamingCreateView.as_view(), name='criar'),
    path('<int:pk>/editar/', views.StreamingUpdateView.as_view(), name='editar'),
    path('<int:pk>/deletar/', views.StreamingDeleteView.as_view(), name='deletar'),
]
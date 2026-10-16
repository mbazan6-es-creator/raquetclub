from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.custom_login_view, name='login'),
    path('logout/', views.custom_logout_view, name='logout'),
    path('', views.home_view, name='home'),
    path('jugadores/', views.player_list_view, name='player_list'),
    path('jugadores/nuevo/', views.player_create_view, name='player_create'),
    path('jugadores/<int:pk>/', views.player_detail_view, name='player_detail'),
    path('jugadores/<int:pk>/editar/', views.player_edit_view, name='player_edit'),
    path('cobros/', views.pending_debts_view, name='pending_debts'),
    path('cobros/<int:pk>/pagar/', views.collect_payment_view, name='collect_payment'),
    path('rendicion/', views.financial_report_view, name='financial_report'),
    path('mensualidades/nueva/', views.create_fee_view, name='create_fee'),
    
    # Módulo de Configuración de Usuarios (Accesible desde la Tuerca ⚙️)
    path('usuarios/', views.user_list_view, name='user_list'),
    path('usuarios/nuevo/', views.user_create_view, name='user_create'),
    path('usuarios/<int:pk>/password/', views.user_password_change_view, name='user_password_change'),
    path('usuarios/<int:pk>/eliminar/', views.user_delete_view, name='user_delete'),
]
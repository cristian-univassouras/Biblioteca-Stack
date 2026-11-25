from django.urls import path

from core import views as core_views

from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('login/', core_views.CustomLoginView.as_view(), name='login'),
    path('cadastro/', core_views.cadastro_organizacao, name='cadastro'),
    path('logout/', core_views.logout_view, name='logout'),

    path('equipe/', core_views.lista_equipe, name='lista_equipe'),
    path('equipe/novo/', core_views.novo_usuario_equipe, name='novo_usuario_equipe'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/exportar/csv/', views.exportar_csv, name='exportar_csv'),
    path('dashboard/exportar/pdf/', views.exportar_pdf, name='exportar_pdf'),

    path('livros/', views.lista_livros, name='lista'),
    path('livros/novo/', views.novo_livro, name='novo_livro'),
    path('livros/<int:pk>/editar/', views.editar_livro, name='editar_livro'),
    path('livros/<int:pk>/apagar/', views.apagar_livro, name='apagar_livro'),

    path('autores/', views.lista_autores, name='lista_autores'),
    path('autores/novo/', views.novo_autor, name='novo_autor'),
    path('autores/<int:pk>/editar/', views.editar_autor, name='editar_autor'),
    path('autores/<int:pk>/apagar/', views.apagar_autor, name='apagar_autor'),

    path('exemplares/', views.lista_exemplares, name='lista_exemplares'),
    path('exemplares/novo/', views.novo_exemplar, name='novo_exemplar'),
    path('exemplares/<int:pk>/editar/', views.editar_exemplar, name='editar_exemplar'),
    path('exemplares/<int:pk>/apagar/', views.apagar_exemplar, name='apagar_exemplar'),

    path('membros/', views.lista_membros, name='lista_membros'),
    path('membros/novo/', views.novo_membro, name='novo_membro'),
    path('membros/<int:pk>/editar/', views.editar_membro, name='editar_membro'),
    path('membros/<int:pk>/apagar/', views.apagar_membro, name='apagar_membro'),

    path('emprestimos/', views.lista_emprestimos, name='lista_emprestimos'),
    path('emprestimos/novo/', views.novo_emprestimo, name='novo_emprestimo'),
    path('emprestimos/<int:pk>/devolver/', views.devolver_emprestimo, name='devolver_emprestimo'),

    path('reservas/', views.lista_reservas, name='lista_reservas'),
    path('reservas/nova/', views.nova_reserva, name='nova_reserva'),
    path('reservas/<int:pk>/cancelar/', views.cancelar_reserva, name='cancelar_reserva'),
]

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import CadastroOrganizacaoForm, NovoUsuarioEquipeForm
from .models import Organizacao, Perfil
from .permissions import obter_perfil, org_atual, papel_requerido


class CustomLoginView(auth_views.LoginView):
    """Direciona usuários de organização para o dashboard e superusuários para o /admin/."""

    template_name = 'acervo/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.get_redirect_url()
        if next_url:
            return next_url
        perfil = obter_perfil(self.request.user)
        if perfil is None and self.request.user.is_superuser:
            return reverse('admin:index')
        return reverse('dashboard')


def cadastro_organizacao(request):
    """Permite que uma nova biblioteca se cadastre criando Organização + Admin."""
    if request.user.is_authenticated:
        perfil = obter_perfil(request.user)
        if perfil is not None:
            return redirect('dashboard')
        if request.user.is_superuser:
            return redirect('admin:index')

    if request.method == 'POST':
        form = CadastroOrganizacaoForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                org = Organizacao.objects.create(
                    nome=form.cleaned_data['nome_organizacao'].strip()
                )
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                )
                Perfil.objects.create(usuario=user, organizacao=org, papel='admin')
            login(request, user)
            messages.success(
                request,
                f'Organização "{org.nome}" criada! Bem-vindo(a), {user.username}.',
            )
            return redirect('dashboard')
    else:
        form = CadastroOrganizacaoForm()

    return render(request, 'acervo/cadastro.html', {'form': form})


@papel_requerido('admin')
def lista_equipe(request):
    """Lista apenas os usuários pertencentes à organização do administrador logado."""
    org = org_atual(request)
    membros_equipe = Perfil.objects.select_related('usuario').filter(organizacao=org).order_by('usuario__username')
    return render(
        request,
        'acervo/equipe.html',
        {'membros_equipe': membros_equipe, 'organizacao': org},
    )


@papel_requerido('admin')
def novo_usuario_equipe(request):
    """Permite ao administrador criar operadores ou outros admins dentro da própria organização."""
    org = org_atual(request)
    if request.method == 'POST':
        form = NovoUsuarioEquipeForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                )
                Perfil.objects.create(
                    usuario=user,
                    organizacao=org,
                    papel=form.cleaned_data['papel'],
                )
            messages.success(
                request,
                f'Usuário "{user.username}" adicionado à organização {org.nome}.',
            )
            return redirect('lista_equipe')
    else:
        form = NovoUsuarioEquipeForm()

    return render(
        request,
        'acervo/form.html',
        {'form': form, 'titulo_pagina': f'Novo usuário — {org.nome}'},
    )

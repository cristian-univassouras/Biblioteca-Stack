from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Perfil


def obter_perfil(user):
    """Retorna o Perfil do usuário ou None caso não exista (ex.: superuser sem perfil)."""
    if not user or not user.is_authenticated:
        return None
    try:
        return user.perfil
    except Perfil.DoesNotExist:
        return None


def org_atual(request):
    """Retorna a organização do usuário autenticado."""
    return request.user.perfil.organizacao


def perfil_requerido(view_func):
    """Garante que o usuário está autenticado e possui um Perfil vinculado a uma Organização."""

    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if obter_perfil(request.user) is None:
            messages.warning(
                request,
                'Sua conta não possui um perfil vinculado a uma organização. '
                'Vincule um perfil no painel administrativo para acessar esta área.',
            )
            if request.user.is_staff:
                return redirect('admin:index')
            return render(request, 'acervo/sem_perfil.html', status=403)
        return view_func(request, *args, **kwargs)

    return _wrapped


def papel_requerido(*papeis):
    """Restringe uma view aos usuários cujo Perfil tenha um dos papéis informados."""

    def decorator(view_func):
        @perfil_requerido
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.perfil.papel not in papeis:
                return HttpResponseForbidden(
                    'Acesso negado: seu perfil não tem permissão para esta ação.'
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


class TemPerfilAtivo(BasePermission):
    """Permissão DRF: usuário autenticado precisa ter Perfil com organização vinculada."""

    message = 'Usuário autenticado sem perfil/organização vinculados.'

    def has_permission(self, request, view):
        return obter_perfil(request.user) is not None


class AdminParaEscritaOuExclusao(BasePermission):
    """Permite leitura/criação/edição para operador e restringe DELETE ao papel admin."""

    message = 'Apenas administradores da organização podem remover registros.'

    def has_permission(self, request, view):
        perfil = obter_perfil(request.user)
        if perfil is None:
            return False
        if request.method == 'DELETE':
            return perfil.eh_admin
        return True


class SomenteAdmin(BasePermission):
    """Permissão DRF restrita a administradores da organização."""

    message = 'Apenas administradores da organização têm acesso a este recurso.'

    def has_permission(self, request, view):
        perfil = obter_perfil(request.user)
        return perfil is not None and (perfil.eh_admin or request.method in SAFE_METHODS)

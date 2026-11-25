from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    AutorViewSet,
    DashboardApi,
    EmprestimoViewSet,
    ExemplarViewSet,
    LivroViewSet,
    MembroViewSet,
    ReservaViewSet,
)

router = DefaultRouter()
router.register('autores', AutorViewSet, basename='api-autor')
router.register('livros', LivroViewSet, basename='api-livro')
router.register('exemplares', ExemplarViewSet, basename='api-exemplar')
router.register('membros', MembroViewSet, basename='api-membro')
router.register('emprestimos', EmprestimoViewSet, basename='api-emprestimo')
router.register('reservas', ReservaViewSet, basename='api-reserva')

urlpatterns = [
    path('dashboard/', DashboardApi.as_view(), name='api_dashboard'),
    path('', include(router.urls)),
]

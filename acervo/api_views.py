from datetime import date

from django.db import transaction
from django.db.models import ProtectedError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import AdminParaEscritaOuExclusao, TemPerfilAtivo, org_atual

from .dashboard import base_emprestimos_filtrada, calcular_metricas_dashboard
from .models import Autor, Emprestimo, Exemplar, Livro, Membro, Reserva
from .serializers import (
    AutorSerializer,
    EmprestimoSerializer,
    ExemplarSerializer,
    LivroSerializer,
    MembroSerializer,
    ReservaSerializer,
)


class OrganizacaoViewSetMixin:
    """Isola automaticamente consultas, criações e exclusões pela organização do usuário."""

    permission_classes = [IsAuthenticated, TemPerfilAtivo, AdminParaEscritaOuExclusao]

    def get_queryset(self):
        return super().get_queryset().filter(organizacao=org_atual(self.request))

    def perform_create(self, serializer):
        serializer.save(organizacao=org_atual(self.request))

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': 'Não é possível remover este registro porque há outros dados vinculados a ele.'},
                status=status.HTTP_409_CONFLICT,
            )


class AutorViewSet(OrganizacaoViewSetMixin, viewsets.ModelViewSet):
    queryset = Autor.objects.all()
    serializer_class = AutorSerializer


class LivroViewSet(OrganizacaoViewSetMixin, viewsets.ModelViewSet):
    queryset = Livro.objects.select_related('autor').all()
    serializer_class = LivroSerializer


class ExemplarViewSet(OrganizacaoViewSetMixin, viewsets.ModelViewSet):
    queryset = Exemplar.objects.select_related('livro').all()
    serializer_class = ExemplarSerializer


class MembroViewSet(OrganizacaoViewSetMixin, viewsets.ModelViewSet):
    queryset = Membro.objects.all()
    serializer_class = MembroSerializer


class EmprestimoViewSet(OrganizacaoViewSetMixin, viewsets.ModelViewSet):
    queryset = Emprestimo.objects.select_related('exemplar__livro', 'membro').all()
    serializer_class = EmprestimoSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        emprestimo = serializer.save(organizacao=org_atual(self.request))
        emprestimo.exemplar.estado = 'emprestado'
        emprestimo.exemplar.save(update_fields=['estado'])

    @transaction.atomic
    def perform_destroy(self, instance):
        exemplar = instance.exemplar
        estava_aberto = instance.data_devolucao is None
        instance.delete()
        if estava_aberto:
            exemplar.estado = 'disponivel'
            exemplar.save(update_fields=['estado'])

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def devolver(self, request, pk=None):
        emprestimo = self.get_object()
        if emprestimo.data_devolucao is not None:
            return Response(
                {'detail': 'Este empréstimo já foi devolvido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        emprestimo.data_devolucao = date.today()
        emprestimo.save(update_fields=['data_devolucao'])

        exemplar = emprestimo.exemplar
        exemplar.estado = 'disponivel'
        exemplar.save(update_fields=['estado'])

        proxima_reserva = Reserva.objects.filter(
            organizacao=org_atual(request),
            livro=exemplar.livro,
            atendida=False,
        ).first()
        if proxima_reserva:
            proxima_reserva.atendida = True
            proxima_reserva.save(update_fields=['atendida'])

        return Response(self.get_serializer(emprestimo).data)


class ReservaViewSet(OrganizacaoViewSetMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, TemPerfilAtivo]
    queryset = Reserva.objects.select_related('livro', 'membro').all()
    serializer_class = ReservaSerializer


class DashboardApi(APIView):
    """Expõe as métricas do dashboard da organização autenticada em JSON."""

    permission_classes = [IsAuthenticated, TemPerfilAtivo]

    def get(self, request):
        org = org_atual(request)
        base, periodo_form = base_emprestimos_filtrada(request, org)
        agrupamento = (
            periodo_form.cleaned_data.get('agrupamento') or 'mes'
            if periodo_form.is_valid()
            else 'mes'
        )
        metricas = calcular_metricas_dashboard(
            base,
            org,
            incluir_series=request.user.perfil.eh_admin,
            agrupamento=agrupamento,
        )
        return Response(metricas)

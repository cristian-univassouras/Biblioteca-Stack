from datetime import date

from rest_framework import serializers

from .models import Autor, Emprestimo, Exemplar, Livro, Membro, Reserva


class OrganizacaoSerializerMixin:
    """Fornece acesso seguro à organização do usuário logado dentro do serializer."""

    def _org_atual(self):
        request = self.context.get('request')
        if request and hasattr(request.user, 'perfil'):
            return request.user.perfil.organizacao
        return None

    def _validar_mesma_org(self, obj, nome_campo):
        org = self._org_atual()
        if org is not None and obj.organizacao_id != org.id:
            raise serializers.ValidationError(
                f'O {nome_campo} selecionado não pertence à sua organização.'
            )
        return obj


class AutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Autor
        fields = ['id', 'nome', 'imagem_url']


class LivroSerializer(OrganizacaoSerializerMixin, serializers.ModelSerializer):
    autor_nome = serializers.CharField(source='autor.nome', read_only=True)

    class Meta:
        model = Livro
        fields = [
            'id',
            'titulo',
            'autor',
            'autor_nome',
            'ano',
            'tipo_acervo',
            'categoria',
            'imagem_url',
        ]

    def validate_autor(self, value):
        return self._validar_mesma_org(value, 'autor')

    def validate_ano(self, value):
        if value > date.today().year:
            raise serializers.ValidationError(
                'O ano de publicação não pode ser um ano futuro.'
            )
        return value


class ExemplarSerializer(OrganizacaoSerializerMixin, serializers.ModelSerializer):
    livro_titulo = serializers.CharField(source='livro.titulo', read_only=True)

    class Meta:
        model = Exemplar
        fields = ['id', 'livro', 'livro_titulo', 'codigo_patrimonio', 'estado']

    def validate_livro(self, value):
        return self._validar_mesma_org(value, 'livro')

    def validate_codigo_patrimonio(self, value):
        org = self._org_atual()
        if org is not None:
            qs = Exemplar.objects.filter(organizacao=org, codigo_patrimonio=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    'Já existe um exemplar com este código de patrimônio nesta organização.'
                )
        return value


class MembroSerializer(OrganizacaoSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Membro
        fields = ['id', 'nome', 'email', 'data_cadastro']
        read_only_fields = ['data_cadastro']

    def validate_email(self, value):
        org = self._org_atual()
        if org is not None:
            qs = Membro.objects.filter(organizacao=org, email=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    'Já existe um membro cadastrado com este e-mail nesta organização.'
                )
        return value


class EmprestimoSerializer(OrganizacaoSerializerMixin, serializers.ModelSerializer):
    livro_titulo = serializers.CharField(source='exemplar.livro.titulo', read_only=True)
    membro_nome = serializers.CharField(source='membro.nome', read_only=True)
    dias_atraso = serializers.IntegerField(read_only=True)
    multa = serializers.FloatField(read_only=True)

    class Meta:
        model = Emprestimo
        fields = [
            'id',
            'exemplar',
            'livro_titulo',
            'membro',
            'membro_nome',
            'data_emprestimo',
            'data_prevista_devolucao',
            'data_devolucao',
            'valor_multa_diaria',
            'dias_atraso',
            'multa',
        ]
        read_only_fields = ['data_emprestimo', 'data_devolucao', 'dias_atraso', 'multa']

    def validate_exemplar(self, value):
        self._validar_mesma_org(value, 'exemplar')
        if self.instance is None and value.estado != 'disponivel':
            raise serializers.ValidationError('Este exemplar não está disponível para empréstimo.')
        return value

    def validate_membro(self, value):
        return self._validar_mesma_org(value, 'membro')

    def validate_data_prevista_devolucao(self, value):
        referencia = (
            self.instance.data_emprestimo
            if self.instance and self.instance.data_emprestimo
            else date.today()
        )
        if value < referencia:
            raise serializers.ValidationError(
                'A data prevista de devolução não pode ser anterior ao empréstimo.'
            )
        return value


class ReservaSerializer(OrganizacaoSerializerMixin, serializers.ModelSerializer):
    livro_titulo = serializers.CharField(source='livro.titulo', read_only=True)
    membro_nome = serializers.CharField(source='membro.nome', read_only=True)

    class Meta:
        model = Reserva
        fields = ['id', 'livro', 'livro_titulo', 'membro', 'membro_nome', 'data_reserva', 'atendida']
        read_only_fields = ['data_reserva', 'atendida']

    def validate_livro(self, value):
        return self._validar_mesma_org(value, 'livro')

    def validate_membro(self, value):
        return self._validar_mesma_org(value, 'membro')

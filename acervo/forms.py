import calendar
import re
from datetime import date, datetime, timedelta

from django import forms

from .models import Autor, Emprestimo, Exemplar, Livro, Membro, Reserva


class LivroForm(forms.ModelForm):
    class Meta:
        model = Livro
        fields = ['titulo', 'autor', 'ano', 'tipo_acervo', 'categoria', 'imagem_url']

    def __init__(self, *args, org=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.org = org
        self.fields['autor'].empty_label = 'Selecione um autor'
        self.fields['autor'].queryset = (
            Autor.objects.filter(organizacao=org) if org is not None else Autor.objects.none()
        )

    def clean_ano(self):
        ano = self.cleaned_data.get('ano')
        if ano and ano > date.today().year:
            raise forms.ValidationError('O ano de publicação não pode ser um ano futuro.')
        return ano


class AutorForm(forms.ModelForm):
    class Meta:
        model = Autor
        fields = ['nome', 'imagem_url']


class ExemplarForm(forms.ModelForm):
    class Meta:
        model = Exemplar
        fields = ['livro', 'codigo_patrimonio', 'estado']

    def __init__(self, *args, org=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.org = org
        self.fields['livro'].empty_label = 'Selecione um livro'
        self.fields['livro'].queryset = (
            Livro.objects.filter(organizacao=org) if org is not None else Livro.objects.none()
        )

    def clean_codigo_patrimonio(self):
        codigo = self.cleaned_data.get('codigo_patrimonio')
        if codigo and self.org is not None:
            existe = (
                Exemplar.objects.filter(organizacao=self.org, codigo_patrimonio=codigo)
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if existe:
                raise forms.ValidationError(
                    'Já existe um exemplar com este código de patrimônio nesta organização.'
                )
        return codigo


class MembroForm(forms.ModelForm):
    class Meta:
        model = Membro
        fields = ['nome', 'email']

    def __init__(self, *args, org=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.org = org

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and self.org is not None:
            existe = (
                Membro.objects.filter(organizacao=self.org, email=email)
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if existe:
                raise forms.ValidationError(
                    'Já existe um membro cadastrado com este e-mail nesta organização.'
                )
        return email


class EmprestimoForm(forms.ModelForm):
    class Meta:
        model = Emprestimo
        fields = ['exemplar', 'membro', 'data_prevista_devolucao']
        widgets = {
            'data_prevista_devolucao': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, org=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.org = org
        self.fields['exemplar'].queryset = (
            Exemplar.objects.filter(organizacao=org, estado='disponivel').select_related('livro')
            if org is not None
            else Exemplar.objects.none()
        )
        self.fields['exemplar'].empty_label = 'Selecione um exemplar disponível'
        self.fields['membro'].queryset = (
            Membro.objects.filter(organizacao=org) if org is not None else Membro.objects.none()
        )
        self.fields['membro'].empty_label = 'Selecione um membro'

    def clean_data_prevista_devolucao(self):
        data_prevista = self.cleaned_data.get('data_prevista_devolucao')
        referencia = (
            self.instance.data_emprestimo
            if self.instance and self.instance.pk and self.instance.data_emprestimo
            else date.today()
        )
        if data_prevista and data_prevista < referencia:
            raise forms.ValidationError(
                'A data prevista de devolução não pode ser anterior ao empréstimo.'
            )
        return data_prevista


class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ['livro', 'membro']

    def __init__(self, *args, org=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.org = org
        self.fields['livro'].queryset = (
            Livro.objects.filter(organizacao=org) if org is not None else Livro.objects.none()
        )
        self.fields['livro'].empty_label = 'Selecione um livro'
        self.fields['membro'].queryset = (
            Membro.objects.filter(organizacao=org) if org is not None else Membro.objects.none()
        )
        self.fields['membro'].empty_label = 'Selecione um membro'


class PeriodoForm(forms.Form):
    ATALHO_CHOICES = [
        ('', 'Personalizado'),
        ('semana', 'Últimos 7 dias'),
        ('mes', 'Mês atual'),
    ]
    AGRUPAMENTO_CHOICES = [
        ('mes', 'Por mês'),
        ('semana', 'Por semana'),
    ]

    atalho = forms.ChoiceField(required=False, choices=ATALHO_CHOICES, label='Atalho')
    mes = forms.CharField(
        required=False,
        label='Mês',
        widget=forms.TextInput(attrs={'type': 'month'}),
    )
    semana = forms.CharField(
        required=False,
        label='Semana',
        widget=forms.TextInput(attrs={'type': 'week'}),
    )
    inicio = forms.DateField(
        required=False,
        label='Início',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    fim = forms.DateField(
        required=False,
        label='Fim',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    agrupamento = forms.ChoiceField(
        required=False,
        choices=AGRUPAMENTO_CHOICES,
        initial='mes',
        label='Série temporal',
    )

    def clean_mes(self):
        valor = (self.cleaned_data.get('mes') or '').strip()
        if not valor:
            return ''
        try:
            datetime.strptime(valor, '%Y-%m')
        except ValueError as exc:
            raise forms.ValidationError('Informe um mês válido (AAAA-MM).') from exc
        return valor

    def clean_semana(self):
        valor = (self.cleaned_data.get('semana') or '').strip()
        if not valor:
            return ''
        match = re.fullmatch(r'(\d{4})-W(\d{2})', valor)
        if not match:
            raise forms.ValidationError('Informe uma semana válida (AAAA-Wss).')
        ano, sem = int(match.group(1)), int(match.group(2))
        try:
            date.fromisocalendar(ano, sem, 1)
        except ValueError as exc:
            raise forms.ValidationError('Semana ISO inválida.') from exc
        return valor


def resolver_intervalo_periodo(form):
    """Converte os filtros validados (datas, mês, semana ou atalho) em (inicio, fim, rótulo)."""
    if not form.is_valid():
        return None, None, 'Todos os registros'

    data = form.cleaned_data
    inicio = data.get('inicio')
    fim = data.get('fim')
    if inicio or fim:
        inicio_txt = inicio.strftime('%d/%m/%Y') if inicio else 'Início'
        fim_txt = fim.strftime('%d/%m/%Y') if fim else 'Hoje'
        return inicio, fim, f'{inicio_txt} até {fim_txt}'

    mes_str = data.get('mes')
    if mes_str:
        dt = datetime.strptime(mes_str, '%Y-%m')
        ultimo_dia = calendar.monthrange(dt.year, dt.month)[1]
        return date(dt.year, dt.month, 1), date(dt.year, dt.month, ultimo_dia), f'Mês {dt.strftime("%m/%Y")}'

    semana_str = data.get('semana')
    if semana_str:
        match = re.fullmatch(r'(\d{4})-W(\d{2})', semana_str)
        ano, sem = int(match.group(1)), int(match.group(2))
        segunda = date.fromisocalendar(ano, sem, 1)
        domingo = segunda + timedelta(days=6)
        return segunda, domingo, f'Semana {sem:02d}/{ano} ({segunda.strftime("%d/%m")} a {domingo.strftime("%d/%m")})'

    hoje = date.today()
    atalho = data.get('atalho')
    if atalho == 'semana':
        return hoje - timedelta(days=6), hoje, 'Últimos 7 dias'
    if atalho == 'mes':
        return date(hoje.year, hoje.month, 1), hoje, f'Mês atual ({hoje.strftime("%m/%Y")})'

    return None, None, 'Todos os registros'


def filtrar_periodo(request, qs, campo='data_emprestimo'):
    """Filtra um queryset de forma segura usando PeriodoForm validado."""
    form = PeriodoForm(request.GET)
    inicio, fim, _ = resolver_intervalo_periodo(form)
    if inicio:
        qs = qs.filter(**{f'{campo}__gte': inicio})
    if fim:
        qs = qs.filter(**{f'{campo}__lte': fim})
    return qs, form

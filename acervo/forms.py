from datetime import date

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


def filtrar_periodo(request, qs, campo='data_emprestimo'):
    """Filtra um queryset de forma segura usando PeriodoForm validado."""
    form = PeriodoForm(request.GET)
    if form.is_valid():
        if form.cleaned_data.get('inicio'):
            qs = qs.filter(**{f'{campo}__gte': form.cleaned_data['inicio']})
        if form.cleaned_data.get('fim'):
            qs = qs.filter(**{f'{campo}__lte': form.cleaned_data['fim']})
    return qs, form

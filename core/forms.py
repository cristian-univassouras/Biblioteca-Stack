from django import forms
from django.contrib.auth.models import User

from .models import Perfil


class CadastroOrganizacaoForm(forms.Form):
    nome_organizacao = forms.CharField(
        label='Nome da biblioteca / organização',
        max_length=120,
        widget=forms.TextInput(attrs={'placeholder': 'Ex.: Biblioteca Municipal de Vassouras'}),
    )
    username = forms.CharField(
        label='Usuário administrador',
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Ex.: maria_silva'}),
    )
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={'placeholder': 'maria@biblioteca.com'}),
    )
    password = forms.CharField(
        label='Senha',
        min_length=6,
        widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo de 6 caracteres'}),
    )
    confirmar_password = forms.CharField(
        label='Confirmar senha',
        widget=forms.PasswordInput(attrs={'placeholder': 'Repita a senha'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Este nome de usuário já está em uso.')
        return username

    def clean(self):
        cleaned = super().clean()
        senha = cleaned.get('password')
        confirmacao = cleaned.get('confirmar_password')
        if senha and confirmacao and senha != confirmacao:
            self.add_error('confirmar_password', 'As senhas não conferem.')
        return cleaned


class NovoUsuarioEquipeForm(forms.Form):
    username = forms.CharField(
        label='Nome de usuário',
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Ex.: joao_operador'}),
    )
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={'placeholder': 'joao@biblioteca.com'}),
    )
    papel = forms.ChoiceField(
        label='Papel na organização',
        choices=Perfil.PAPEIS,
        initial='operador',
    )
    password = forms.CharField(
        label='Senha inicial',
        min_length=6,
        widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo de 6 caracteres'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Este nome de usuário já está em uso.')
        return username

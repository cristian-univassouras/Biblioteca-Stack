from django.contrib.auth.models import User
from django.db import models


class Organizacao(models.Model):
    """Representa uma biblioteca/inquilino no modelo multi-tenant."""

    nome = models.CharField(max_length=120)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Organização'
        verbose_name_plural = 'Organizações'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class DaOrganizacao(models.Model):
    """Base abstrata para isolar todos os modelos de negócio por organização."""

    organizacao = models.ForeignKey(
        'core.Organizacao',
        on_delete=models.PROTECT,
        related_name='%(class)s_registros',
    )

    class Meta:
        abstract = True


class Perfil(models.Model):
    """Estende o User do Django vinculando-o a uma organização e a um papel."""

    PAPEIS = [
        ('admin', 'Administrador'),
        ('operador', 'Operador'),
    ]

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil',
    )
    organizacao = models.ForeignKey(
        Organizacao,
        on_delete=models.PROTECT,
        related_name='perfis',
    )
    papel = models.CharField(max_length=20, choices=PAPEIS, default='operador')

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'

    @property
    def eh_admin(self):
        return self.papel == 'admin'

    def __str__(self):
        return f'{self.usuario.username} — {self.organizacao.nome} ({self.get_papel_display()})'

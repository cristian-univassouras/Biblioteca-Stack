from django.contrib import admin

from .models import Autor, Emprestimo, Exemplar, Livro, Membro, Reserva


@admin.register(Autor)
class AutorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'organizacao')
    list_filter = ('organizacao',)
    search_fields = ('nome',)


@admin.register(Livro)
class LivroAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'autor', 'ano', 'tipo_acervo', 'categoria', 'organizacao')
    list_filter = ('organizacao', 'tipo_acervo', 'categoria')
    search_fields = ('titulo', 'autor__nome')


@admin.register(Exemplar)
class ExemplarAdmin(admin.ModelAdmin):
    list_display = ('codigo_patrimonio', 'livro', 'estado', 'organizacao')
    list_filter = ('organizacao', 'estado')
    search_fields = ('codigo_patrimonio', 'livro__titulo')


@admin.register(Membro)
class MembroAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'data_cadastro', 'organizacao')
    list_filter = ('organizacao',)
    search_fields = ('nome', 'email')


@admin.register(Emprestimo)
class EmprestimoAdmin(admin.ModelAdmin):
    list_display = ('exemplar', 'membro', 'data_emprestimo', 'data_prevista_devolucao', 'data_devolucao', 'organizacao')
    list_filter = ('organizacao', 'data_devolucao')
    search_fields = ('exemplar__livro__titulo', 'membro__nome')


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('livro', 'membro', 'data_reserva', 'atendida', 'organizacao')
    list_filter = ('organizacao', 'atendida')
    search_fields = ('livro__titulo', 'membro__nome')

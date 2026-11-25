from datetime import date, timedelta

from django.contrib import messages
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render

from core.permissions import org_atual, papel_requerido, perfil_requerido

from .dashboard import (
    base_emprestimos_filtrada,
    calcular_metricas_dashboard,
    gerar_resposta_csv,
    gerar_resposta_pdf,
)
from .forms import (
    AutorForm,
    EmprestimoForm,
    ExemplarForm,
    LivroForm,
    MembroForm,
    ReservaForm,
)
from .models import Autor, Emprestimo, Exemplar, Livro, Membro, Reserva

FUNCIONALIDADES = [
    {'icone': '🏢', 'titulo': 'Multi-organização',
     'texto': 'Várias bibliotecas na mesma base com isolamento total de dados por organização.'},
    {'icone': '🔐', 'titulo': 'Perfis e permissões',
     'texto': 'Controle de acesso para Administradores e Operadores em todas as telas e API.'},
    {'icone': '📊', 'titulo': 'Dashboard e relatórios',
     'texto': 'KPIs, rankings, séries temporais, gráficos e exportação em CSV e PDF.'},
    {'icone': '🔌', 'titulo': 'API REST com DRF',
     'texto': 'Endpoints em JSON com serializers, validações e autenticação integrada.'},
    {'icone': '🤝', 'titulo': 'Empréstimos e reservas',
     'texto': 'Prazo de devolução, cálculo automático de multa e fila automática de reservas.'},
    {'icone': '🐳', 'titulo': 'Docker + PostgreSQL',
     'texto': 'Ambiente containerizado pronto para subir aplicação e banco de dados.'},
]


LIVROS_VITRINE = [
    {'numero': '01', 'titulo': 'Dom Casmurro', 'autor': 'Machado de Assis', 'ano': 1899,
     'categoria': '800 – Literatura', 'capa': 'acervo/covers/cover-01.svg',
     'resumo': 'Ciúme, memória e ironia na obra-prima de Machado de Assis.'},
    {'numero': '02', 'titulo': 'Vidas Secas', 'autor': 'Graciliano Ramos', 'ano': 1938,
     'categoria': '800 – Literatura', 'capa': 'acervo/covers/cover-02.svg',
     'resumo': 'A travessia de Fabiano e sua família pelo sertão nordestino.'},
    {'numero': '03', 'titulo': 'A Hora da Estrela', 'autor': 'Clarice Lispector', 'ano': 1977,
     'categoria': '800 – Literatura', 'capa': 'acervo/covers/cover-03.svg',
     'resumo': 'O retrato delicado e cortante de Macabéa no Rio de Janeiro.'},
    {'numero': '04', 'titulo': 'Grande Sertão: Veredas', 'autor': 'Guimarães Rosa', 'ano': 1956,
     'categoria': '800 – Literatura', 'capa': 'acervo/covers/cover-04.svg',
     'resumo': 'Linguagem inventiva e épica na jornada de Riobaldo.'},
    {'numero': '05', 'titulo': 'Capitães da Areia', 'autor': 'Jorge Amado', 'ano': 1937,
     'categoria': '800 – Literatura', 'capa': 'acervo/covers/cover-05.svg',
     'resumo': 'Juventude, liberdade e resistência nas ruas de Salvador.'},
    {'numero': '06', 'titulo': 'Iracema', 'autor': 'José de Alencar', 'ano': 1865,
     'categoria': '800 – Literatura', 'capa': 'acervo/covers/cover-06.svg',
     'resumo': 'Poema em prosa que marca o romantismo brasileiro.'},
    {'numero': '07', 'titulo': 'O Quinze', 'autor': 'Rachel de Queiroz', 'ano': 1930,
     'categoria': '800 – Literatura', 'capa': 'acervo/covers/cover-07.svg',
     'resumo': 'Marco do romance social brasileiro sobre a seca de 1915.'},
    {'numero': '08', 'titulo': 'Sentimento do Mundo', 'autor': 'Carlos Drummond', 'ano': 1940,
     'categoria': '800 – Poesia', 'capa': 'acervo/covers/cover-08.svg',
     'resumo': 'Versos essenciais sobre empatia, tempo e vida coletiva.'},
    {'numero': '09', 'titulo': 'Policarpo Quaresma', 'autor': 'Lima Barreto', 'ano': 1911,
     'categoria': '300 – Clássicos', 'capa': 'acervo/covers/cover-09.svg',
     'resumo': 'Sátira afiada sobre idealismo e burocracia na Primeira República.'},
    {'numero': '10', 'titulo': 'Romanceiro da Inconfidência', 'autor': 'Cecília Meireles', 'ano': 1953,
     'categoria': '900 – História', 'capa': 'acervo/covers/cover-10.svg',
     'resumo': 'Lirismo histórico sobre Vila Rica e os inconfidentes.'},
    {'numero': '11', 'titulo': 'Cosmos', 'autor': 'Carl Sagan', 'ano': 1980,
     'categoria': '500 – Ciências', 'capa': 'acervo/covers/cover-11.svg',
     'resumo': 'Uma viagem inspiradora pela ciência, astronomia e humanidade.'},
    {'numero': '12', 'titulo': 'Sapiens', 'autor': 'Yuval N. Harari', 'ano': 2011,
     'categoria': '900 – História', 'capa': 'acervo/covers/cover-12.svg',
     'resumo': 'Da revolução cognitiva à era da informação em perspectiva.'},
    {'numero': '13', 'titulo': 'Python Fluente', 'autor': 'Luciano Ramalho', 'ano': 2015,
     'categoria': '600 – Tecnologia', 'capa': 'acervo/covers/cover-13.svg',
     'resumo': 'Boas práticas e programação idiomática em Python moderno.'},
    {'numero': '14', 'titulo': 'Pedagogia da Autonomia', 'autor': 'Paulo Freire', 'ano': 1996,
     'categoria': '300 – Educação', 'capa': 'acervo/covers/cover-14.svg',
     'resumo': 'Saberes fundamentais para uma prática educativa libertadora.'},
    {'numero': '15', 'titulo': 'Sistemas Operacionais', 'autor': 'A. Tanenbaum', 'ano': 2015,
     'categoria': '600 – Tecnologia', 'capa': 'acervo/covers/cover-15.svg',
     'resumo': 'Arquitetura, processos e fundamentos da computação moderna.'},
    {'numero': '16', 'titulo': 'Reinações de Narizinho', 'autor': 'Monteiro Lobato', 'ano': 1931,
     'categoria': '800 – Infantil', 'capa': 'acervo/covers/cover-16.svg',
     'resumo': 'Imaginação e folclore no universo do Sítio do Picapau Amarelo.'},
]


def home(request):
    return render(
        request,
        'acervo/home.html',
        {
            'funcionalidades': FUNCIONALIDADES,
            'livros_vitrine': LIVROS_VITRINE,
        },
    )


@perfil_requerido
def dashboard(request):
    org = org_atual(request)
    base, periodo_form = base_emprestimos_filtrada(request, org)
    eh_admin = request.user.perfil.eh_admin
    metricas = calcular_metricas_dashboard(base, org, incluir_series=eh_admin)

    contexto = {
        'organizacao': org,
        'form_periodo': periodo_form,
        'mostra_series': eh_admin,
        'pode_exportar': eh_admin,
        'kpis': metricas['kpis'],
        'ranking': metricas['ranking'],
        'por_mes': metricas['por_mes'],
        'por_categoria': metricas['por_categoria'],
        'exemplares_por_estado': metricas['exemplares_por_estado'],
    }
    return render(request, 'acervo/dashboard.html', contexto)


@papel_requerido('admin')
def exportar_csv(request):
    org = org_atual(request)
    base, _ = base_emprestimos_filtrada(request, org)
    return gerar_resposta_csv(base)


@papel_requerido('admin')
def exportar_pdf(request):
    org = org_atual(request)
    base, periodo_form = base_emprestimos_filtrada(request, org)
    return gerar_resposta_pdf(base, org, periodo_form, request.user)


@perfil_requerido
def lista_livros(request):
    org = org_atual(request)
    livros = Livro.objects.select_related('autor').filter(organizacao=org)

    nome = request.GET.get('nome', '')
    tipo = request.GET.get('tipo', '')
    categoria = request.GET.get('categoria', '')

    condicao = Q()
    if nome:
        condicao &= Q(titulo__icontains=nome) | Q(autor__nome__icontains=nome)
    if tipo:
        condicao &= Q(tipo_acervo=tipo)
    if categoria:
        condicao &= Q(categoria=categoria)

    livros = livros.filter(condicao)

    return render(
        request,
        'acervo/lista.html',
        {
            'livros': livros,
            'tipos': Livro.TIPO_ACERVO_CHOICES,
            'categorias': Livro.CATEGORIA_CHOICES,
            'filtro_nome': nome,
            'filtro_tipo': tipo,
            'filtro_categoria': categoria,
        },
    )


@perfil_requerido
def novo_livro(request):
    org = org_atual(request)
    if request.method == 'POST':
        form = LivroForm(request.POST, org=org)
        if form.is_valid():
            livro = form.save(commit=False)
            livro.organizacao = org
            livro.save()
            messages.success(request, 'Livro cadastrado com sucesso.')
            return redirect('lista')
    else:
        form = LivroForm(org=org)
    return render(request, 'acervo/form.html', {'form': form, 'titulo_pagina': 'Novo livro'})


@perfil_requerido
def editar_livro(request, pk):
    org = org_atual(request)
    livro = get_object_or_404(Livro, pk=pk, organizacao=org)
    if request.method == 'POST':
        form = LivroForm(request.POST, instance=livro, org=org)
        if form.is_valid():
            form.save()
            messages.success(request, 'Livro atualizado com sucesso.')
            return redirect('lista')
    else:
        form = LivroForm(instance=livro, org=org)
    return render(request, 'acervo/form.html', {'form': form, 'titulo_pagina': 'Editar livro'})


@papel_requerido('admin')
def apagar_livro(request, pk):
    org = org_atual(request)
    livro = get_object_or_404(Livro, pk=pk, organizacao=org)
    if request.method == 'POST':
        try:
            livro.delete()
            messages.success(request, 'Livro removido com sucesso.')
        except ProtectedError:
            messages.error(request, 'Não é possível remover este livro porque há registros vinculados.')
        return redirect('lista')
    return render(request, 'acervo/confirmar_exclusao.html', {'objeto': livro, 'voltar_url': 'lista'})


@perfil_requerido
def lista_autores(request):
    org = org_atual(request)
    autores = Autor.objects.filter(organizacao=org)

    nome = request.GET.get('nome', '')
    if nome:
        autores = autores.filter(nome__icontains=nome)

    return render(request, 'acervo/autores.html', {'autores': autores, 'filtro_nome': nome})


@perfil_requerido
def novo_autor(request):
    org = org_atual(request)
    if request.method == 'POST':
        form = AutorForm(request.POST)
        if form.is_valid():
            autor = form.save(commit=False)
            autor.organizacao = org
            autor.save()
            messages.success(request, 'Autor cadastrado com sucesso.')
            return redirect('lista_autores')
    else:
        form = AutorForm()
    return render(request, 'acervo/form.html', {'form': form, 'titulo_pagina': 'Novo autor'})


@perfil_requerido
def editar_autor(request, pk):
    org = org_atual(request)
    autor = get_object_or_404(Autor, pk=pk, organizacao=org)
    if request.method == 'POST':
        form = AutorForm(request.POST, instance=autor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Autor atualizado com sucesso.')
            return redirect('lista_autores')
    else:
        form = AutorForm(instance=autor)
    return render(request, 'acervo/form.html', {'form': form, 'titulo_pagina': 'Editar autor'})


@papel_requerido('admin')
def apagar_autor(request, pk):
    org = org_atual(request)
    autor = get_object_or_404(Autor, pk=pk, organizacao=org)
    if request.method == 'POST':
        try:
            autor.delete()
            messages.success(request, 'Autor removido com sucesso.')
        except ProtectedError:
            messages.error(request, 'Não é possível remover este autor porque existem livros vinculados a ele.')
        return redirect('lista_autores')
    return render(request, 'acervo/confirmar_exclusao.html', {'objeto': autor, 'voltar_url': 'lista_autores'})


@perfil_requerido
def lista_exemplares(request):
    org = org_atual(request)
    exemplares = Exemplar.objects.select_related('livro').filter(organizacao=org)

    nome = request.GET.get('nome', '')
    estado = request.GET.get('estado', '')

    condicao = Q()
    if nome:
        condicao &= Q(livro__titulo__icontains=nome) | Q(codigo_patrimonio__icontains=nome)
    if estado:
        condicao &= Q(estado=estado)

    exemplares = exemplares.filter(condicao)

    return render(
        request,
        'acervo/exemplares.html',
        {
            'exemplares': exemplares,
            'estados': Exemplar.ESTADO_CHOICES,
            'filtro_nome': nome,
            'filtro_estado': estado,
        },
    )


@perfil_requerido
def novo_exemplar(request):
    org = org_atual(request)
    if request.method == 'POST':
        form = ExemplarForm(request.POST, org=org)
        if form.is_valid():
            exemplar = form.save(commit=False)
            exemplar.organizacao = org
            exemplar.save()
            messages.success(request, 'Exemplar cadastrado com sucesso.')
            return redirect('lista_exemplares')
    else:
        form = ExemplarForm(org=org)
    return render(request, 'acervo/form.html', {'form': form, 'titulo_pagina': 'Novo exemplar'})


@perfil_requerido
def editar_exemplar(request, pk):
    org = org_atual(request)
    exemplar = get_object_or_404(Exemplar, pk=pk, organizacao=org)
    if request.method == 'POST':
        form = ExemplarForm(request.POST, instance=exemplar, org=org)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exemplar atualizado com sucesso.')
            return redirect('lista_exemplares')
    else:
        form = ExemplarForm(instance=exemplar, org=org)
    return render(request, 'acervo/form.html', {'form': form, 'titulo_pagina': 'Editar exemplar'})


@papel_requerido('admin')
def apagar_exemplar(request, pk):
    org = org_atual(request)
    exemplar = get_object_or_404(Exemplar, pk=pk, organizacao=org)
    if request.method == 'POST':
        try:
            exemplar.delete()
            messages.success(request, 'Exemplar removido com sucesso.')
        except ProtectedError:
            messages.error(request, 'Não é possível remover este exemplar porque existem empréstimos vinculados.')
        return redirect('lista_exemplares')
    return render(request, 'acervo/confirmar_exclusao.html', {'objeto': exemplar, 'voltar_url': 'lista_exemplares'})


@perfil_requerido
def lista_membros(request):
    org = org_atual(request)
    membros = Membro.objects.filter(organizacao=org)

    nome = request.GET.get('nome', '')
    if nome:
        membros = membros.filter(Q(nome__icontains=nome) | Q(email__icontains=nome))

    return render(request, 'acervo/membros.html', {'membros': membros, 'filtro_nome': nome})


@perfil_requerido
def novo_membro(request):
    org = org_atual(request)
    if request.method == 'POST':
        form = MembroForm(request.POST, org=org)
        if form.is_valid():
            membro = form.save(commit=False)
            membro.organizacao = org
            membro.save()
            messages.success(request, 'Membro cadastrado com sucesso.')
            return redirect('lista_membros')
    else:
        form = MembroForm(org=org)
    return render(request, 'acervo/form.html', {'form': form, 'titulo_pagina': 'Novo membro'})


@perfil_requerido
def editar_membro(request, pk):
    org = org_atual(request)
    membro = get_object_or_404(Membro, pk=pk, organizacao=org)
    if request.method == 'POST':
        form = MembroForm(request.POST, instance=membro, org=org)
        if form.is_valid():
            form.save()
            messages.success(request, 'Membro atualizado com sucesso.')
            return redirect('lista_membros')
    else:
        form = MembroForm(instance=membro, org=org)
    return render(request, 'acervo/form.html', {'form': form, 'titulo_pagina': 'Editar membro'})


@papel_requerido('admin')
def apagar_membro(request, pk):
    org = org_atual(request)
    membro = get_object_or_404(Membro, pk=pk, organizacao=org)
    if request.method == 'POST':
        try:
            membro.delete()
            messages.success(request, 'Membro removido com sucesso.')
        except ProtectedError:
            messages.error(request, 'Não é possível remover este membro porque existem empréstimos vinculados.')
        return redirect('lista_membros')
    return render(request, 'acervo/confirmar_exclusao.html', {'objeto': membro, 'voltar_url': 'lista_membros'})


@perfil_requerido
def lista_emprestimos(request):
    org = org_atual(request)
    emprestimos = Emprestimo.objects.select_related('exemplar__livro', 'membro').filter(organizacao=org)

    nome = request.GET.get('nome', '')
    situacao = request.GET.get('situacao', '')

    condicao = Q()
    if nome:
        condicao &= Q(exemplar__livro__titulo__icontains=nome) | Q(membro__nome__icontains=nome)
    if situacao == 'aberto':
        condicao &= Q(data_devolucao__isnull=True)
    elif situacao == 'devolvido':
        condicao &= Q(data_devolucao__isnull=False)

    emprestimos = emprestimos.filter(condicao)

    return render(
        request,
        'acervo/emprestimos.html',
        {'emprestimos': emprestimos, 'filtro_nome': nome, 'filtro_situacao': situacao},
    )


@perfil_requerido
def novo_emprestimo(request):
    org = org_atual(request)
    if request.method == 'POST':
        form = EmprestimoForm(request.POST, org=org)
        if form.is_valid():
            with transaction.atomic():
                emprestimo = form.save(commit=False)
                emprestimo.organizacao = org
                emprestimo.save()
                emprestimo.exemplar.estado = 'emprestado'
                emprestimo.exemplar.save(update_fields=['estado'])
            messages.success(request, 'Empréstimo registrado com sucesso.')
            return redirect('lista_emprestimos')
    else:
        form = EmprestimoForm(
            initial={'data_prevista_devolucao': date.today() + timedelta(days=14)},
            org=org,
        )
    return render(request, 'acervo/form.html', {'form': form, 'titulo_pagina': 'Novo empréstimo'})


@perfil_requerido
def devolver_emprestimo(request, pk):
    org = org_atual(request)
    emprestimo = get_object_or_404(Emprestimo, pk=pk, organizacao=org)
    if request.method == 'POST':
        if emprestimo.data_devolucao is not None:
            messages.warning(request, 'Este empréstimo já foi devolvido.')
            return redirect('lista_emprestimos')

        with transaction.atomic():
            emprestimo.data_devolucao = date.today()
            emprestimo.save(update_fields=['data_devolucao'])

            exemplar = emprestimo.exemplar
            exemplar.estado = 'disponivel'
            exemplar.save(update_fields=['estado'])

            proxima_reserva = Reserva.objects.filter(
                organizacao=org,
                livro=exemplar.livro,
                atendida=False,
            ).first()
            if proxima_reserva:
                proxima_reserva.atendida = True
                proxima_reserva.save(update_fields=['atendida'])

        messages.success(request, 'Devolução registrada com sucesso.')

    return redirect('lista_emprestimos')


@perfil_requerido
def lista_reservas(request):
    org = org_atual(request)
    reservas = Reserva.objects.select_related('livro', 'membro').filter(organizacao=org)

    nome = request.GET.get('nome', '')
    situacao = request.GET.get('situacao', '')

    condicao = Q()
    if nome:
        condicao &= Q(livro__titulo__icontains=nome) | Q(membro__nome__icontains=nome)
    if situacao == 'aguardando':
        condicao &= Q(atendida=False)
    elif situacao == 'atendida':
        condicao &= Q(atendida=True)

    reservas = reservas.filter(condicao)

    return render(
        request,
        'acervo/reservas.html',
        {'reservas': reservas, 'filtro_nome': nome, 'filtro_situacao': situacao},
    )


@perfil_requerido
def nova_reserva(request):
    org = org_atual(request)
    if request.method == 'POST':
        form = ReservaForm(request.POST, org=org)
        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.organizacao = org
            reserva.save()
            messages.success(request, 'Reserva registrada com sucesso.')
            return redirect('lista_reservas')
    else:
        form = ReservaForm(org=org)
    return render(request, 'acervo/form.html', {'form': form, 'titulo_pagina': 'Nova reserva'})


@perfil_requerido
def cancelar_reserva(request, pk):
    org = org_atual(request)
    reserva = get_object_or_404(Reserva, pk=pk, organizacao=org)
    if request.method == 'POST':
        reserva.delete()
        messages.success(request, 'Reserva cancelada com sucesso.')
        return redirect('lista_reservas')
    return render(
        request,
        'acervo/confirmar_exclusao.html',
        {'objeto': reserva, 'voltar_url': 'lista_reservas'},
    )

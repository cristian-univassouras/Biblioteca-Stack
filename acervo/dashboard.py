import csv
import io
from datetime import date, datetime
from xml.sax.saxutils import escape

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .forms import filtrar_periodo
from .models import Emprestimo, Exemplar, Livro, Reserva

CATEGORIA_MAP = dict(Livro.CATEGORIA_CHOICES)
ESTADO_MAP = dict(Exemplar.ESTADO_CHOICES)


def base_emprestimos_filtrada(request, org):
    """Retorna a base de empréstimos filtrada por organização e período validado."""
    qs = Emprestimo.objects.filter(organizacao=org)
    return filtrar_periodo(request, qs)


def calcular_metricas_dashboard(base, org, incluir_series=True):
    """Calcula todas as métricas do dashboard via ORM sem N+1."""
    hoje = date.today()

    kpis = base.aggregate(
        total=Count('id'),
        leitores=Count('membro', distinct=True),
        abertos=Count('id', filter=Q(data_devolucao__isnull=True)),
        atrasados=Count(
            'id',
            filter=Q(data_devolucao__isnull=True, data_prevista_devolucao__lt=hoje),
        ),
    )

    acervo_kpis = Exemplar.objects.filter(organizacao=org).aggregate(
        total_exemplares=Count('id'),
        disponiveis=Count('id', filter=Q(estado='disponivel')),
    )
    reservas_aguardando = Reserva.objects.filter(organizacao=org, atendida=False).count()

    kpis.update(acervo_kpis)
    kpis['reservas_aguardando'] = reservas_aguardando

    ranking_qs = (
        base.values('exemplar__livro__titulo')
        .annotate(total=Count('id'))
        .order_by('-total', 'exemplar__livro__titulo')[:5]
    )
    ranking = [
        {'titulo': item['exemplar__livro__titulo'], 'total': item['total']}
        for item in ranking_qs
    ]

    categoria_qs = (
        base.values('exemplar__livro__categoria')
        .annotate(total=Count('id'))
        .order_by('-total', 'exemplar__livro__categoria')
    )
    por_categoria = [
        {
            'categoria': CATEGORIA_MAP.get(
                item['exemplar__livro__categoria'],
                item['exemplar__livro__categoria'],
            ),
            'total': item['total'],
        }
        for item in categoria_qs
    ]

    estado_qs = (
        Exemplar.objects.filter(organizacao=org)
        .values('estado')
        .annotate(total=Count('id'))
        .order_by('estado')
    )
    exemplares_por_estado = [
        {
            'estado': ESTADO_MAP.get(item['estado'], item['estado']),
            'total': item['total'],
        }
        for item in estado_qs
    ]

    por_mes = []
    if incluir_series:
        por_mes_qs = (
            base.annotate(mes=TruncMonth('data_emprestimo'))
            .values('mes')
            .annotate(total=Count('id'))
            .order_by('mes')
        )
        por_mes = [
            {'mes': r['mes'].strftime('%m/%Y'), 'total': r['total']}
            for r in por_mes_qs
            if r['mes'] is not None
        ]

    return {
        'kpis': kpis,
        'ranking': ranking,
        'por_mes': por_mes,
        'por_categoria': por_categoria,
        'exemplares_por_estado': exemplares_por_estado,
    }


def sanitizar_celula_csv(valor):
    """Previne formula injection no Excel para células iniciadas por =, +, - ou @."""
    texto = str(valor)
    if texto and texto[0] in ('=', '+', '-', '@', '\t', '\r'):
        return f"'{texto}"
    return texto


def gerar_resposta_csv(base):
    """Gera HttpResponse CSV com a base já filtrada por organização e período."""
    qs = base.select_related('exemplar__livro', 'membro').order_by('-data_emprestimo', '-id')

    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = 'attachment; filename="emprestimos.csv"'
    resp.write('\ufeff')

    writer = csv.writer(resp)
    writer.writerow([
        'Livro',
        'Patrimônio',
        'Membro',
        'Data Empréstimo',
        'Previsto Devolução',
        'Data Devolução',
        'Dias Atraso',
        'Multa (R$)',
    ])

    for e in qs:
        writer.writerow([
            sanitizar_celula_csv(e.exemplar.livro.titulo),
            sanitizar_celula_csv(e.exemplar.codigo_patrimonio),
            sanitizar_celula_csv(e.membro.nome),
            e.data_emprestimo.strftime('%d/%m/%Y'),
            e.data_prevista_devolucao.strftime('%d/%m/%Y'),
            e.data_devolucao.strftime('%d/%m/%Y') if e.data_devolucao else 'Em aberto',
            e.dias_atraso,
            f'{e.multa:.2f}',
        ])

    return resp


def gerar_resposta_pdf(base, org, form, usuario):
    """Gera HttpResponse PDF com resumo de KPIs e tabela de empréstimos filtrados."""
    qs = base.select_related('exemplar__livro', 'membro').order_by('-data_emprestimo', '-id')
    kpis = base.aggregate(
        total=Count('id'),
        abertos=Count('id', filter=Q(data_devolucao__isnull=True)),
        leitores=Count('membro', distinct=True),
        atrasados=Count(
            'id',
            filter=Q(data_devolucao__isnull=True, data_prevista_devolucao__lt=date.today()),
        ),
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    elementos = []

    elementos.append(Paragraph(f'Relatório de Empréstimos — {escape(org.nome)}', styles['Title']))

    inicio = form.cleaned_data.get('inicio') if form.is_valid() else None
    fim = form.cleaned_data.get('fim') if form.is_valid() else None
    if inicio or fim:
        inicio_txt = inicio.strftime('%d/%m/%Y') if inicio else 'Início'
        fim_txt = fim.strftime('%d/%m/%Y') if fim else 'Hoje'
        periodo_txt = f'Período: {inicio_txt} até {fim_txt}'
    else:
        periodo_txt = 'Período: Todos os registros'

    meta_txt = (
        f'{periodo_txt} | Emitido por: {escape(usuario.username)} | '
        f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M")}'
    )
    elementos.append(Paragraph(meta_txt, styles['Normal']))
    elementos.append(Spacer(1, 0.4 * cm))

    resumo = Paragraph(
        f'<b>Total de empréstimos:</b> {kpis["total"]} &nbsp;&nbsp;|&nbsp;&nbsp; '
        f'<b>Em aberto:</b> {kpis["abertos"]} &nbsp;&nbsp;|&nbsp;&nbsp; '
        f'<b>Em atraso:</b> {kpis["atrasados"]} &nbsp;&nbsp;|&nbsp;&nbsp; '
        f'<b>Membros ativos:</b> {kpis["leitores"]}',
        styles['Normal'],
    )
    elementos.append(resumo)
    elementos.append(Spacer(1, 0.5 * cm))

    dados = [[
        'Livro',
        'Patrimônio',
        'Membro',
        'Empréstimo',
        'Previsto',
        'Devolução',
        'Atraso',
        'Multa',
    ]]

    for e in qs:
        dados.append([
            e.exemplar.livro.titulo[:42],
            e.exemplar.codigo_patrimonio,
            e.membro.nome[:28],
            e.data_emprestimo.strftime('%d/%m/%Y'),
            e.data_prevista_devolucao.strftime('%d/%m/%Y'),
            e.data_devolucao.strftime('%d/%m/%Y') if e.data_devolucao else 'Em aberto',
            f'{e.dias_atraso}d',
            f'R$ {e.multa:.2f}',
        ])

    if len(dados) == 1:
        dados.append(['Nenhum empréstimo encontrado no período.', '', '', '', '', '', '', ''])

    tabela = Table(
        dados,
        colWidths=[7.5 * cm, 3.0 * cm, 5.0 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 1.8 * cm, 2.2 * cm],
        repeatRows=1,
    )
    tabela.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f4f6f8')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d7de')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (3, 1), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ])
    )
    elementos.append(tabela)

    doc.build(elementos)
    buffer.seek(0)

    resp = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="relatorio_emprestimos.pdf"'
    return resp

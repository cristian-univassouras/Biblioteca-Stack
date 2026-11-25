from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import Organizacao, Perfil

from .forms import EmprestimoForm, ExemplarForm, LivroForm, MembroForm, ReservaForm
from .models import Autor, Emprestimo, Exemplar, Livro, Membro, Reserva


class BaseMultiTenantMixin:
    @classmethod
    def criar_cenario_base(cls):
        cls.org_a = Organizacao.objects.create(nome='Biblioteca Central')
        cls.org_b = Organizacao.objects.create(nome='Biblioteca do Bairro')

        cls.admin_a = User.objects.create_user('ana_admin', 'ana@a.com', 'senha1234')
        Perfil.objects.create(usuario=cls.admin_a, organizacao=cls.org_a, papel='admin')

        cls.op_a = User.objects.create_user('ana_op', 'op@a.com', 'senha1234')
        Perfil.objects.create(usuario=cls.op_a, organizacao=cls.org_a, papel='operador')

        cls.admin_b = User.objects.create_user('bruno_admin', 'bruno@b.com', 'senha1234')
        Perfil.objects.create(usuario=cls.admin_b, organizacao=cls.org_b, papel='admin')

        cls.autor_a = Autor.objects.create(organizacao=cls.org_a, nome='Machado de Assis')
        cls.autor_b = Autor.objects.create(organizacao=cls.org_b, nome='Clarice Lispector')

        cls.livro_a = Livro.objects.create(
            organizacao=cls.org_a,
            titulo='Dom Casmurro',
            autor=cls.autor_a,
            ano=1899,
            tipo_acervo='fisico',
            categoria='800',
        )
        cls.livro_b = Livro.objects.create(
            organizacao=cls.org_b,
            titulo='A Hora da Estrela',
            autor=cls.autor_b,
            ano=1977,
            tipo_acervo='fisico',
            categoria='800',
        )

        cls.exemplar_a = Exemplar.objects.create(
            organizacao=cls.org_a,
            livro=cls.livro_a,
            codigo_patrimonio='PAT-100',
            estado='disponivel',
        )
        cls.exemplar_b = Exemplar.objects.create(
            organizacao=cls.org_b,
            livro=cls.livro_b,
            codigo_patrimonio='PAT-200',
            estado='disponivel',
        )

        cls.membro_a = Membro.objects.create(
            organizacao=cls.org_a,
            nome='Carlos Leitor',
            email='carlos@a.com',
        )
        cls.membro_b = Membro.objects.create(
            organizacao=cls.org_b,
            nome='Diana Leitora',
            email='diana@b.com',
        )


class IsolamentoMultiTenantTest(BaseMultiTenantMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.criar_cenario_base()

    def test_listagem_filtra_por_organizacao(self):
        self.client.force_login(self.admin_a)
        resp = self.client.get(reverse('lista'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Dom Casmurro')
        self.assertNotContains(resp, 'A Hora da Estrela')

    def test_acesso_edicao_outra_organizacao_retorna_404(self):
        self.client.force_login(self.admin_a)
        urls_proibidas = [
            reverse('editar_livro', args=[self.livro_b.pk]),
            reverse('editar_autor', args=[self.autor_b.pk]),
            reverse('editar_exemplar', args=[self.exemplar_b.pk]),
            reverse('editar_membro', args=[self.membro_b.pk]),
        ]
        for url in urls_proibidas:
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_criacao_vincula_organizacao_do_usuario(self):
        self.client.force_login(self.admin_a)
        resp = self.client.post(
            reverse('novo_livro'),
            {
                'titulo': 'Memórias Póstumas',
                'autor': self.autor_a.pk,
                'ano': 1881,
                'tipo_acervo': 'fisico',
                'categoria': '800',
                'imagem_url': '',
            },
        )
        self.assertRedirects(resp, reverse('lista'))
        novo = Livro.objects.get(titulo='Memórias Póstumas')
        self.assertEqual(novo.organizacao, self.org_a)

    def test_selects_formulario_filtrados_por_organizacao(self):
        livro_form = LivroForm(org=self.org_a)
        self.assertEqual(list(livro_form.fields['autor'].queryset), [self.autor_a])

        ex_form = ExemplarForm(org=self.org_a)
        self.assertEqual(list(ex_form.fields['livro'].queryset), [self.livro_a])

        emp_form = EmprestimoForm(org=self.org_a)
        self.assertEqual(list(emp_form.fields['exemplar'].queryset), [self.exemplar_a])
        self.assertEqual(list(emp_form.fields['membro'].queryset), [self.membro_a])

        res_form = ReservaForm(org=self.org_a)
        self.assertEqual(list(res_form.fields['livro'].queryset), [self.livro_a])
        self.assertEqual(list(res_form.fields['membro'].queryset), [self.membro_a])

    def test_unicidade_por_organizacao(self):
        # Mesmo código e mesmo e-mail permitidos em orgs diferentes
        ex_b_mesmo_cod = Exemplar.objects.create(
            organizacao=self.org_b,
            livro=self.livro_b,
            codigo_patrimonio='PAT-100',
            estado='disponivel',
        )
        self.assertEqual(ex_b_mesmo_cod.codigo_patrimonio, 'PAT-100')

        membro_b_mesmo_email = Membro.objects.create(
            organizacao=self.org_b,
            nome='Outro Carlos',
            email='carlos@a.com',
        )
        self.assertEqual(membro_b_mesmo_email.email, 'carlos@a.com')

        # Duplicado na mesma org deve falhar na validação do form
        form_ex = ExemplarForm(
            {'livro': self.livro_a.pk, 'codigo_patrimonio': 'PAT-100', 'estado': 'disponivel'},
            org=self.org_a,
        )
        self.assertFalse(form_ex.is_valid())
        self.assertIn('codigo_patrimonio', form_ex.errors)

        form_membro = MembroForm(
            {'nome': 'Clone', 'email': 'carlos@a.com'},
            org=self.org_a,
        )
        self.assertFalse(form_membro.is_valid())
        self.assertIn('email', form_membro.errors)


class PerfisEPermissoesTest(BaseMultiTenantMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.criar_cenario_base()

    def test_usuario_sem_login_redireciona(self):
        resp = self.client.get(reverse('lista'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_landing_page_publica_carrega_com_capas_e_vitrine(self):
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'BIBLIOTECA')
        self.assertContains(resp, 'STACK')
        self.assertContains(resp, 'cover-01.svg')
        self.assertContains(resp, 'Dom Casmurro')

    def test_usuario_sem_perfil_nao_gera_erro_500(self):
        super_sem_perfil = User.objects.create_superuser('root', 'root@sys.com', 'senha1234')
        self.client.force_login(super_sem_perfil)
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 403)
        self.assertContains(resp, '/admin/', status_code=403)

        comum_sem_perfil = User.objects.create_user('semperfil', 'sp@sys.com', 'senha1234')
        self.client.force_login(comum_sem_perfil)
        resp2 = self.client.get(reverse('dashboard'))
        self.assertEqual(resp2.status_code, 403)

    def test_superadmin_login_redireciona_para_admin(self):
        User.objects.create_superuser('super_teste', 'super@sys.com', 'senha1234')
        resp = self.client.post(
            reverse('login'),
            {'username': 'super_teste', 'password': 'senha1234'},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.endswith('/admin/'))

    def test_cadastro_cria_nova_organizacao_e_admin_isolado(self):
        resp = self.client.post(
            reverse('cadastro'),
            {
                'nome_organizacao': 'Biblioteca Nova',
                'username': 'dono_novo',
                'email': 'dono@nova.com',
                'password': 'segredo123',
                'confirmar_password': 'segredo123',
            },
        )
        self.assertRedirects(resp, reverse('dashboard'))
        nova_org = Organizacao.objects.get(nome='Biblioteca Nova')
        novo_user = User.objects.get(username='dono_novo')
        self.assertEqual(novo_user.perfil.organizacao, nova_org)
        self.assertEqual(novo_user.perfil.papel, 'admin')

        # Não vê livros de outras organizações
        lista = self.client.get(reverse('lista'))
        self.assertNotContains(lista, 'Dom Casmurro')

    def test_equipe_apenas_admin_lista_e_cria_na_mesma_organizacao(self):
        self.client.force_login(self.op_a)
        self.assertEqual(self.client.get(reverse('lista_equipe')).status_code, 403)
        self.assertEqual(self.client.get(reverse('novo_usuario_equipe')).status_code, 403)

        self.client.force_login(self.admin_a)
        resp_lista = self.client.get(reverse('lista_equipe'))
        self.assertEqual(resp_lista.status_code, 200)
        self.assertContains(resp_lista, 'ana_op')
        self.assertNotContains(resp_lista, 'bruno_admin')

        resp_novo = self.client.post(
            reverse('novo_usuario_equipe'),
            {
                'username': 'novo_op_a',
                'email': 'novoop@a.com',
                'papel': 'operador',
                'password': 'segredo123',
            },
        )
        self.assertRedirects(resp_novo, reverse('lista_equipe'))
        criado = User.objects.get(username='novo_op_a')
        self.assertEqual(criado.perfil.organizacao, self.org_a)
        self.assertEqual(criado.perfil.papel, 'operador')

    def test_logout_redireciona_para_landing_page_em_post_e_get(self):
        self.client.force_login(self.admin_a)
        r_post = self.client.post(reverse('logout'))
        self.assertRedirects(r_post, reverse('home'))
        self.assertFalse(r_post.wsgi_request.user.is_authenticated)

        self.client.force_login(self.admin_a)
        r_get = self.client.get(reverse('logout'))
        self.assertRedirects(r_get, reverse('home'))
        self.assertFalse(r_get.wsgi_request.user.is_authenticated)

    def test_operador_nao_pode_apagar_nem_exportar(self):
        self.client.force_login(self.op_a)
        self.assertEqual(self.client.post(reverse('apagar_livro', args=[self.livro_a.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('exportar_csv')).status_code, 403)
        self.assertEqual(self.client.get(reverse('exportar_pdf')).status_code, 403)

    def test_admin_pode_apagar_sem_vinculo_e_trata_protected_error(self):
        self.client.force_login(self.admin_a)
        # Autor com livro vinculado não gera 500
        resp_protect = self.client.post(reverse('apagar_autor', args=[self.autor_a.pk]))
        self.assertRedirects(resp_protect, reverse('lista_autores'))
        self.assertTrue(Autor.objects.filter(pk=self.autor_a.pk).exists())

        # Livro sem empréstimos pode ser apagado pelo admin
        livro_temp = Livro.objects.create(
            organizacao=self.org_a,
            titulo='Temporário',
            autor=self.autor_a,
            ano=2020,
        )
        resp_del = self.client.post(reverse('apagar_livro', args=[livro_temp.pk]))
        self.assertRedirects(resp_del, reverse('lista'))
        self.assertFalse(Livro.objects.filter(pk=livro_temp.pk).exists())


class DashboardERelatoriosTest(BaseMultiTenantMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.criar_cenario_base()

        # 3 empréstimos na Org A
        for _ in range(3):
            Emprestimo.objects.create(
                organizacao=cls.org_a,
                exemplar=cls.exemplar_a,
                membro=cls.membro_a,
                data_prevista_devolucao=date.today() + timedelta(days=7),
            )

        # 5 empréstimos na Org B
        for _ in range(5):
            Emprestimo.objects.create(
                organizacao=cls.org_b,
                exemplar=cls.exemplar_b,
                membro=cls.membro_b,
                data_prevista_devolucao=date.today() + timedelta(days=7),
            )

    def test_total_da_organizacao(self):
        self.client.force_login(self.admin_a)
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['kpis']['total'], 3)

    def test_filtro_por_periodo_e_parametro_invalido(self):
        self.client.force_login(self.admin_a)
        r_invalido = self.client.get(reverse('dashboard'), {'inicio': 'abc'})
        self.assertEqual(r_invalido.status_code, 200)
        self.assertEqual(r_invalido.context['kpis']['total'], 3)

        amanha = (date.today() + timedelta(days=1)).isoformat()
        r_futuro = self.client.get(reverse('dashboard'), {'inicio': amanha})
        self.assertEqual(r_futuro.status_code, 200)
        self.assertEqual(r_futuro.context['kpis']['total'], 0)

    def test_filtro_por_mes_semana_e_agrupamento(self):
        self.client.force_login(self.admin_a)
        hoje = date.today()
        mes_atual = hoje.strftime('%Y-%m')
        iso_year, iso_week, _ = hoje.isocalendar()
        semana_atual = f'{iso_year}-W{iso_week:02d}'

        r_mes = self.client.get(reverse('dashboard'), {'mes': mes_atual})
        self.assertEqual(r_mes.status_code, 200)
        self.assertEqual(r_mes.context['kpis']['total'], 3)

        r_sem = self.client.get(
            reverse('dashboard'),
            {'semana': semana_atual, 'agrupamento': 'semana'},
        )
        self.assertEqual(r_sem.status_code, 200)
        self.assertEqual(r_sem.context['kpis']['total'], 3)
        self.assertEqual(r_sem.context['agrupamento'], 'semana')
        self.assertTrue(r_sem.context['por_mes'][0]['mes'].startswith('Sem '))

        r_atalho = self.client.get(reverse('dashboard'), {'atalho': 'semana'})
        self.assertEqual(r_atalho.status_code, 200)
        self.assertEqual(r_atalho.context['kpis']['total'], 3)

        # Parâmetros malformados não causam erro 500
        r_errado = self.client.get(reverse('dashboard'), {'mes': 'abc', 'semana': '9999-W99'})
        self.assertEqual(r_errado.status_code, 200)
        self.assertEqual(r_errado.context['kpis']['total'], 3)

    def test_dashboard_vazio_sem_erro(self):
        org_vazia = Organizacao.objects.create(nome='Org Vazia')
        user_vazio = User.objects.create_user('vazio', 'v@v.com', 'senha1234')
        Perfil.objects.create(usuario=user_vazio, organizacao=org_vazia, papel='admin')
        self.client.force_login(user_vazio)
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['kpis']['total'], 0)

    def test_dashboard_papel_operador_oculta_series(self):
        self.client.force_login(self.op_a)
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context['mostra_series'])
        self.assertEqual(r.context['por_mes'], [])

    def test_exportar_csv_sanitiza_formula_e_isola_org(self):
        livro_formula = Livro.objects.create(
            organizacao=self.org_a,
            titulo='=1+1',
            autor=self.autor_a,
            ano=2020,
        )
        ex_formula = Exemplar.objects.create(
            organizacao=self.org_a,
            livro=livro_formula,
            codigo_patrimonio='PAT-FORM',
        )
        Emprestimo.objects.create(
            organizacao=self.org_a,
            exemplar=ex_formula,
            membro=self.membro_a,
            data_prevista_devolucao=date.today() + timedelta(days=5),
        )

        self.client.force_login(self.admin_a)
        resp = self.client.get(reverse('exportar_csv'))
        self.assertEqual(resp.status_code, 200)
        conteudo = resp.content.decode('utf-8')
        self.assertIn("'=1+1", conteudo)
        self.assertNotIn('A Hora da Estrela', conteudo)

    def test_exportar_pdf_retorna_pdf_valido(self):
        self.client.force_login(self.admin_a)
        resp = self.client.get(reverse('exportar_pdf'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content.startswith(b'%PDF'))


class DesempenhoConsultasTest(BaseMultiTenantMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.criar_cenario_base()
        for _ in range(5):
            Emprestimo.objects.create(
                organizacao=cls.org_a,
                exemplar=cls.exemplar_a,
                membro=cls.membro_a,
                data_prevista_devolucao=date.today() + timedelta(days=7),
            )

    def test_emprestimos_com_select_related_sem_n_mais_1(self):
        with self.assertNumQueries(1):
            qs = Emprestimo.objects.select_related('exemplar__livro', 'membro').filter(
                organizacao=self.org_a
            )
            titulos = [f'{e.exemplar.livro.titulo} - {e.membro.nome}' for e in qs]
            self.assertEqual(len(titulos), 5)


class ApiRestDrfTest(BaseMultiTenantMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.criar_cenario_base()

    def setUp(self):
        self.api = APIClient()

    def test_api_exige_autenticacao(self):
        resp = self.api.get('/api/livros/')
        self.assertIn(resp.status_code, (401, 403))
        resp_dash = self.api.get('/api/dashboard/')
        self.assertIn(resp_dash.status_code, (401, 403))

    def test_api_crud_e_isolamento_livros(self):
        self.api.force_authenticate(user=self.admin_a)

        resp_list = self.api.get('/api/livros/')
        self.assertEqual(resp_list.status_code, 200)
        self.assertEqual(len(resp_list.data), 1)
        self.assertEqual(resp_list.data[0]['titulo'], 'Dom Casmurro')

        # Não acessa livro de outra organização
        resp_outro = self.api.get(f'/api/livros/{self.livro_b.pk}/')
        self.assertEqual(resp_outro.status_code, 404)

        # Validação de ano futuro retorna 400
        resp_futuro = self.api.post(
            '/api/livros/',
            {'titulo': 'Futuro', 'autor': self.autor_a.pk, 'ano': date.today().year + 5},
        )
        self.assertEqual(resp_futuro.status_code, 400)

        # Impede vincular autor de outra organização
        resp_autor_b = self.api.post(
            '/api/livros/',
            {'titulo': 'Invasão', 'autor': self.autor_b.pk, 'ano': 2020},
        )
        self.assertEqual(resp_autor_b.status_code, 400)

        # Criação válida vincula organização automaticamente
        resp_ok = self.api.post(
            '/api/livros/',
            {'titulo': 'Quincas Borba', 'autor': self.autor_a.pk, 'ano': 1891},
        )
        self.assertEqual(resp_ok.status_code, 201)
        self.assertEqual(Livro.objects.get(pk=resp_ok.data['id']).organizacao, self.org_a)

    def test_api_operador_nao_pode_deletar_livro(self):
        self.api.force_authenticate(user=self.op_a)
        resp = self.api.delete(f'/api/livros/{self.livro_a.pk}/')
        self.assertEqual(resp.status_code, 403)

    def test_api_emprestimo_devolucao_e_dashboard(self):
        self.api.force_authenticate(user=self.admin_a)

        resp_emp = self.api.post(
            '/api/emprestimos/',
            {
                'exemplar': self.exemplar_a.pk,
                'membro': self.membro_a.pk,
                'data_prevista_devolucao': (date.today() + timedelta(days=7)).isoformat(),
            },
        )
        self.assertEqual(resp_emp.status_code, 201)
        self.exemplar_a.refresh_from_db()
        self.assertEqual(self.exemplar_a.estado, 'emprestado')

        emp_id = resp_emp.data['id']
        resp_dev = self.api.post(f'/api/emprestimos/{emp_id}/devolver/')
        self.assertEqual(resp_dev.status_code, 200)
        self.exemplar_a.refresh_from_db()
        self.assertEqual(self.exemplar_a.estado, 'disponivel')

        resp_dash = self.api.get('/api/dashboard/')
        self.assertEqual(resp_dash.status_code, 200)
        self.assertEqual(resp_dash.data['kpis']['total'], 1)

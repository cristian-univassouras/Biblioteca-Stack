from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from acervo.models import Autor, Emprestimo, Exemplar, Livro, Membro, Reserva
from core.models import Organizacao, Perfil


class Command(BaseCommand):
    help = 'Popula o banco com organizações, usuários separados de superadmin, acervo, empréstimos e reservas.'

    def handle(self, *args, **options):
        # Renomeia a organização legada da P1 para um nome claro de demonstração
        org_legada = Organizacao.objects.filter(nome='Organização padrão').first()
        org_central = Organizacao.objects.filter(nome='Biblioteca Central').first()
        if org_legada and not org_central:
            org_legada.nome = 'Biblioteca Central'
            org_legada.save(update_fields=['nome'])
            org_central = org_legada
        elif not org_central:
            org_central = Organizacao.objects.create(nome='Biblioteca Central')

        org_bairro, _ = Organizacao.objects.get_or_create(nome='Biblioteca do Bairro')

        # Superusuário (dono do sistema / painel /admin/) NÃO tem Perfil vinculado a cliente
        super_user, created = User.objects.get_or_create(
            username='superadmin',
            defaults={'email': 'superadmin@bibliotecastack.local', 'is_staff': True, 'is_superuser': True},
        )
        if created or not super_user.is_superuser:
            super_user.is_staff = True
            super_user.is_superuser = True
            super_user.set_password('super1234')
            super_user.save()
        Perfil.objects.filter(usuario=super_user).delete()

        # Caso exista o antigo usuário 'admin' da demo anterior, garante separação sem perfil de cliente
        antigo_admin = User.objects.filter(username='admin', is_superuser=True).first()
        if antigo_admin:
            Perfil.objects.filter(usuario=antigo_admin).delete()

        # Usuários de cada organização (clientes do SaaS)
        usuarios = [
            ('ana', 'ana@central.local', 'admin1234', org_central, 'admin'),
            ('lucas', 'lucas@central.local', 'oper1234', org_central, 'operador'),
            ('bruno', 'bruno@bairro.local', 'admin1234', org_bairro, 'admin'),
            ('mariana', 'mariana@bairro.local', 'oper1234', org_bairro, 'operador'),
        ]

        for username, email, senha, org, papel in usuarios:
            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={'email': email},
            )
            if user_created:
                user.set_password(senha)
                user.save()
            Perfil.objects.update_or_create(
                usuario=user,
                defaults={'organizacao': org, 'papel': papel},
            )

        self._popular_org_central(org_central)
        self._popular_org_bairro(org_bairro)

        self.stdout.write(self.style.SUCCESS('Banco populado com sucesso para todas as organizações!'))

    def _popular_org_central(self, org):
        dados_livros = [
            ('Machado de Assis', 'https://i.pravatar.cc/300?u=autor-14',
             'Dom Casmurro', 1899, 'fisico', '800', 'https://picsum.photos/seed/livro-13/300/400'),
            ('Clarice Lispector', 'https://i.pravatar.cc/300?u=autor-15',
             'A Hora da Estrela', 1977, 'digital', '800', 'https://picsum.photos/seed/livro-14/300/400'),
            ('José de Alencar', 'https://i.pravatar.cc/300?u=autor-16',
             'Iracema', 1865, 'fisico', '800', 'https://picsum.photos/seed/livro-15/300/400'),
            ('Jorge Amado', 'https://i.pravatar.cc/300?u=autor-17',
             'Capitães da Areia', 1937, 'fisico', '800', 'https://picsum.photos/seed/livro-16/300/400'),
            ('Cecília Meireles', 'https://i.pravatar.cc/300?u=autor-18',
             'Romanceiro da Inconfidência', 1953, 'digital', '900', 'https://picsum.photos/seed/livro-17/300/400'),
            ('Graciliano Ramos', 'https://i.pravatar.cc/300?u=autor-19',
             'Vidas Secas', 1938, 'fisico', '800', 'https://picsum.photos/seed/livro-18/300/400'),
            ('Carlos Drummond de Andrade', 'https://i.pravatar.cc/300?u=autor-20',
             'Sentimento do Mundo', 1940, 'digital', '800', 'https://picsum.photos/seed/livro-19/300/400'),
            ('Guimarães Rosa', 'https://i.pravatar.cc/300?u=autor-21',
             'Grande Sertão: Veredas', 1956, 'fisico', '800', 'https://picsum.photos/seed/livro-20/300/400'),
            ('Lima Barreto', 'https://i.pravatar.cc/300?u=autor-22',
             'Triste Fim de Policarpo Quaresma', 1911, 'fisico', '300', 'https://picsum.photos/seed/livro-21/300/400'),
            ('Rachel de Queiroz', 'https://i.pravatar.cc/300?u=autor-23',
             'O Quinze', 1930, 'digital', '800', 'https://picsum.photos/seed/livro-22/300/400'),
            ('Andrew S. Tanenbaum', 'https://i.pravatar.cc/300?u=autor-24',
             'Sistemas Operacionais Modernos', 2015, 'fisico', '600', 'https://picsum.photos/seed/livro-23/300/400'),
            ('Carl Sagan', 'https://i.pravatar.cc/300?u=autor-25',
             'Cosmos', 1980, 'fisico', '500', 'https://picsum.photos/seed/livro-24/300/400'),
        ]

        livros = []
        for nome_autor, img_autor, titulo, ano, tipo, cat, img_livro in dados_livros:
            autor, _ = Autor.objects.get_or_create(
                organizacao=org,
                nome=nome_autor,
                defaults={'imagem_url': img_autor},
            )
            livro, _ = Livro.objects.get_or_create(
                organizacao=org,
                titulo=titulo,
                defaults={
                    'autor': autor,
                    'ano': ano,
                    'tipo_acervo': tipo,
                    'categoria': cat,
                    'imagem_url': img_livro,
                },
            )
            livros.append(livro)

        estados_ciclo = ['disponivel', 'emprestado', 'disponivel', 'manutencao', 'disponivel']
        exemplares = []
        for idx, livro in enumerate(livros, start=1):
            cod = f'CEN-{idx:03d}'
            ex, _ = Exemplar.objects.get_or_create(
                organizacao=org,
                codigo_patrimonio=cod,
                defaults={
                    'livro': livro,
                    'estado': estados_ciclo[idx % len(estados_ciclo)],
                },
            )
            exemplares.append(ex)

        dados_membros = [
            ('Ana Beatriz Souza', 'ana.souza@central.local'),
            ('Carlos Eduardo Lima', 'carlos.lima@central.local'),
            ('Fernanda Oliveira', 'fernanda.oliveira@central.local'),
            ('Gabriel Martins', 'gabriel.martins@central.local'),
            ('Helena Rodrigues', 'helena.rodrigues@central.local'),
            ('Igor Cavalcanti', 'igor.cavalcanti@central.local'),
            ('Juliana Almeida', 'juliana.almeida@central.local'),
            ('Lucas Barbosa', 'lucas.barbosa@central.local'),
        ]
        membros = []
        for nome_membro, email in dados_membros:
            membro, _ = Membro.objects.get_or_create(
                organizacao=org,
                email=email,
                defaults={'nome': nome_membro},
            )
            membros.append(membro)

        if Emprestimo.objects.filter(organizacao=org).count() < 15:
            hoje = date.today()
            plano_emprestimos = [
                (0, 0, 150, 136),
                (1, 1, 145, 130),
                (2, 2, 120, 108),
                (0, 3, 115, 101),
                (3, 4, 95, 81),
                (10, 5, 90, 76),
                (11, 6, 85, 70),
                (0, 7, 65, 51),
                (5, 0, 60, 46),
                (7, 1, 55, 40),
                (10, 2, 35, 21),
                (0, 3, 30, 16),
                (1, 4, 25, None),
                (3, 5, 10, None),
                (8, 6, 5, None),
            ]
            for ex_idx, mem_idx, dias_atras, devolvido_dias_atras in plano_emprestimos:
                dt_emp = hoje - timedelta(days=dias_atras)
                dt_prev = dt_emp + timedelta(days=14)
                dt_dev = (hoje - timedelta(days=devolvido_dias_atras)) if devolvido_dias_atras is not None else None
                emp = Emprestimo.objects.create(
                    organizacao=org,
                    exemplar=exemplares[ex_idx],
                    membro=membros[mem_idx],
                    data_prevista_devolucao=dt_prev,
                    data_devolucao=dt_dev,
                )
                Emprestimo.objects.filter(pk=emp.pk).update(data_emprestimo=dt_emp)

        if Reserva.objects.filter(organizacao=org).count() < 4:
            Reserva.objects.get_or_create(organizacao=org, livro=livros[0], membro=membros[1], defaults={'atendida': False})
            Reserva.objects.get_or_create(organizacao=org, livro=livros[3], membro=membros[2], defaults={'atendida': False})
            Reserva.objects.get_or_create(organizacao=org, livro=livros[10], membro=membros[4], defaults={'atendida': True})

    def _popular_org_bairro(self, org):
        dados_livros = [
            ('Monteiro Lobato', 'https://i.pravatar.cc/300?u=autor-31',
             'Reinações de Narizinho', 1931, 'fisico', '800', 'https://picsum.photos/seed/livro-31/300/400'),
            ('Cora Coralina', 'https://i.pravatar.cc/300?u=autor-32',
             'Poemas dos Becos de Goiás', 1965, 'fisico', '800', 'https://picsum.photos/seed/livro-32/300/400'),
            ('Milton Santos', 'https://i.pravatar.cc/300?u=autor-33',
             'Por uma Outra Globalização', 2000, 'fisico', '900', 'https://picsum.photos/seed/livro-33/300/400'),
            ('Paulo Freire', 'https://i.pravatar.cc/300?u=autor-34',
             'Pedagogia da Autonomia', 1996, 'digital', '300', 'https://picsum.photos/seed/livro-34/300/400'),
            ('Luciano Ramalho', 'https://i.pravatar.cc/300?u=autor-35',
             'Python Fluente', 2015, 'digital', '600', 'https://picsum.photos/seed/livro-35/300/400'),
            ('Yuval Noah Harari', 'https://i.pravatar.cc/300?u=autor-36',
             'Sapiens: Uma Breve História da Humanidade', 2011, 'fisico', '900', 'https://picsum.photos/seed/livro-36/300/400'),
        ]

        livros = []
        for nome_autor, img_autor, titulo, ano, tipo, cat, img_livro in dados_livros:
            autor, _ = Autor.objects.get_or_create(
                organizacao=org,
                nome=nome_autor,
                defaults={'imagem_url': img_autor},
            )
            livro, _ = Livro.objects.get_or_create(
                organizacao=org,
                titulo=titulo,
                defaults={
                    'autor': autor,
                    'ano': ano,
                    'tipo_acervo': tipo,
                    'categoria': cat,
                    'imagem_url': img_livro,
                },
            )
            livros.append(livro)

        estados = ['disponivel', 'emprestado', 'disponivel', 'disponivel', 'manutencao', 'emprestado']
        exemplares = []
        for idx, livro in enumerate(livros, start=1):
            cod = f'BAI-{idx:03d}'
            ex, _ = Exemplar.objects.get_or_create(
                organizacao=org,
                codigo_patrimonio=cod,
                defaults={'livro': livro, 'estado': estados[idx - 1]},
            )
            exemplares.append(ex)

        dados_membros = [
            ('Bruno Costa', 'bruno@bairro.local'),
            ('Mariana Ribeiro', 'mariana@bairro.local'),
            ('Pedro Henrique', 'pedro@bairro.local'),
            ('Sofia Mendes', 'sofia@bairro.local'),
            ('Thiago Moreira', 'thiago@bairro.local'),
        ]
        membros = []
        for nome_membro, email in dados_membros:
            membro, _ = Membro.objects.get_or_create(
                organizacao=org,
                email=email,
                defaults={'nome': nome_membro},
            )
            membros.append(membro)

        if Emprestimo.objects.filter(organizacao=org).count() < 10:
            hoje = date.today()
            plano = [
                (0, 0, 120, 108),
                (3, 1, 95, 82),
                (4, 2, 90, 77),
                (0, 3, 65, 52),
                (5, 4, 60, 47),
                (4, 0, 35, 22),
                (2, 1, 30, 17),
                (1, 2, 20, None),
                (5, 3, 8, None),
            ]
            for ex_idx, mem_idx, dias_atras, devolvido_dias_atras in plano:
                dt_emp = hoje - timedelta(days=dias_atras)
                dt_prev = dt_emp + timedelta(days=14)
                dt_dev = (hoje - timedelta(days=devolvido_dias_atras)) if devolvido_dias_atras is not None else None
                emp = Emprestimo.objects.create(
                    organizacao=org,
                    exemplar=exemplares[ex_idx],
                    membro=membros[mem_idx],
                    data_prevista_devolucao=dt_prev,
                    data_devolucao=dt_dev,
                )
                Emprestimo.objects.filter(pk=emp.pk).update(data_emprestimo=dt_emp)

        if Reserva.objects.filter(organizacao=org).count() < 2:
            Reserva.objects.get_or_create(organizacao=org, livro=livros[4], membro=membros[0], defaults={'atendida': False})
            Reserva.objects.get_or_create(organizacao=org, livro=livros[5], membro=membros[1], defaults={'atendida': False})

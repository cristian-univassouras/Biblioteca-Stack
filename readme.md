# Biblioteca Stack — Sistema de Gestão de Bibliotecas (Mini-SaaS)

Aplicação web **Mini-SaaS** em Django para gerenciamento multi-organização de bibliotecas, evoluída da **P1** (MVP em Django puro) para a **P2** na disciplina **Laboratório de Programação Full Stack** (Universidade de Vassouras).

---

## Como o Sistema Funciona

### 1. Arquitetura Multi-organização (Multi-tenant)
- Várias bibliotecas compartilham a mesma aplicação e o mesmo banco de dados com **isolamento total por organização** (`core.Organizacao`).
- Todos os modelos de negócio (`Autor`, `Livro`, `Exemplar`, `Membro`, `Emprestimo` e `Reserva`) herdam da classe abstrata `DaOrganizacao` (`ForeignKey` para `Organizacao`).
- Toda listagem, busca, formulário (incluindo opções de `select`), edição/exclusão (`get_object_or_404(..., organizacao=org)`), dashboard, exportação e endpoint da API filtra automaticamente pela organização do usuário autenticado.
- Unicidade por organização via `UniqueConstraint`: bibliotecas diferentes podem cadastrar o mesmo `codigo_patrimonio` de exemplar ou o mesmo `email` de membro, mas duplicidades dentro da mesma organização são bloqueadas.

### 2. Autenticação, Cadastro e Separação de Perfis
- **Landing Page (`/`):** página pública de apresentação com vitrine interativa de livros, acesso rápido para **Entrar** (`/login/`) ou **Cadastrar biblioteca** (`/cadastro/`).
- **Criar Organização (`/cadastro/`):** qualquer nova biblioteca pode se cadastrar pela própria interface. O sistema cria em transação atômica a `Organizacao`, o usuário inicial e seu `Perfil` com papel de **Administrador**, fazendo login automático em um ambiente isolado.
- **Gestão de Equipe (`/equipe/`):** administradores podem visualizar e cadastrar novos **Operadores** ou **Administradores** pertencentes exclusivamente à sua biblioteca.
- **Superadmin (`/admin/`):** conta global do dono da plataforma (`is_superuser=True`, **sem `Perfil` vinculado a nenhuma biblioteca**). Ao entrar, é direcionado ao Django Admin global e não se mistura com os dados operacionais das organizações clientes.

#### Permissões por Papel

| Funcionalidade | Administrador (`admin`) | Operador (`operador`) |
|---|---|---|
| Listar, cadastrar e editar livros, autores, exemplares e membros | Sim | Sim |
| Registrar e devolver empréstimos / criar e cancelar reservas | Sim | Sim |
| Apagar livros, autores, exemplares e membros (Web e API `DELETE`) | Sim | Não (`403`) |
| Dashboard: KPIs gerais, ranking e distribuição | Sim | Sim |
| Dashboard: série temporal mensal e exportação **CSV / PDF** | Sim | Não (`403`) |
| Gerenciar equipe da organização (`/equipe/`) | Sim | Não (`403`) |

### 3. Regras de Negócio da Biblioteca
- **Acervo e Exemplares:** livros classificados por tipo (`Físico` / `Digital`) e classificação Dewey (`000` a `900`), com validação no model/form/API que impede ano de publicação futuro. Cada cópia física/digital possui código de patrimônio e estado (`Disponível`, `Emprestado`, `Em manutenção`).
- **Empréstimos e Devoluções:** operações atômicas (`transaction.atomic()`). Ao emprestar, o exemplar passa para `Emprestado` e a data prevista não pode ser anterior ao empréstimo. Ao devolver, calcula atraso e multa diária, retorna o exemplar para `Disponível`, impede devolução duplicada e atende automaticamente a reserva mais antiga daquele livro.
- **Integridade:** exclusões protegidas por `PROTECT` capturam `ProtectedError` exibindo aviso amigável na interface (ou `409 Conflict` na API).

### 4. Dashboard Analítico e Relatórios (`/dashboard/`)
- Métricas calculadas diretamente no ORM (`aggregate`, `annotate`, `Count(..., filter=Q(...))`, `TruncMonth`) sem consultas N+1 e com índices compostos por organização/data.
- **Filtro por período validado** (`PeriodoForm` com datas `inicio` e `fim`), resistente a parâmetros inválidos na URL.
- **Visualizações recomendadas (Chart.js, sem gráficos de pizza):**
  - Cartões de KPI (total de empréstimos, em aberto, em atraso, membros ativos, exemplares disponíveis e reservas aguardando).
  - **Gráfico de Linha:** evolução mensal dos empréstimos (visível para administradores).
  - **Gráfico de Barras Horizontais + Tabela:** Top 5 livros mais emprestados.
  - **Gráficos de Barras:** distribuição por categoria Dewey e exemplares por estado atual.
- **Exportação:** relatórios com o mesmo filtro de organização e período em **CSV** (UTF-8 com BOM e proteção contra *formula injection* do Excel) e **PDF** (gerado em memória com ReportLab).

### 5. API REST (`/api/`)
Construída com **Django REST Framework**, exige autenticação (`IsAuthenticated` + `TemPerfilAtivo`), usa serializers com campos explícitos e valida relacionamentos entre registros da mesma organização:

| Endpoint | Métodos | Descrição |
|---|---|---|
| `/api/autores/` e `/api/autores/<id>/` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | CRUD de autores da organização |
| `/api/livros/` e `/api/livros/<id>/` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | CRUD de livros da organização |
| `/api/exemplares/` e `/api/exemplares/<id>/` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | CRUD de exemplares |
| `/api/membros/` e `/api/membros/<id>/` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | CRUD de membros |
| `/api/emprestimos/` e `/api/emprestimos/<id>/` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | Registro e gestão de empréstimos |
| `/api/emprestimos/<id>/devolver/` | `POST` | Registra devolução, libera exemplar e atende fila de reserva |
| `/api/reservas/` e `/api/reservas/<id>/` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | Fila de reservas |
| `/api/dashboard/` | `GET` | Métricas do dashboard em JSON (aceita `?inicio=YYYY-MM-DD&fim=YYYY-MM-DD`) |

---

## Como Iniciar o Projeto

### Opção 1: Com Docker + PostgreSQL (Recomendado)

Pré-requisitos: **Docker** e **Docker Compose** (Docker Desktop ativo no Windows/macOS).

1. Clone o repositório e entre na pasta:
   ```bash
   git clone https://github.com/cristian-univassouras/Biblioteca-Stack.git
   cd Biblioteca-Stack
   ```

2. *(Opcional)* Crie o arquivo `.env` a partir do exemplo para personalizar chaves/senhas:
   ```bash
   cp .env.example .env
   ```

3. Suba o banco **PostgreSQL 16** e a aplicação **Django (Gunicorn)**:
   ```bash
   docker compose up -d --build
   ```

   O entrypoint (`docker-entrypoint.sh`) aguarda o PostgreSQL ficar saudável, aplica automaticamente todas as migrações e executa o comando `seed_demo` para popular dados iniciais e contas de demonstração.

4. Acesse no navegador:
   - **Landing Page:** `http://127.0.0.1:8000/`
   - **Login:** `http://127.0.0.1:8000/login/`
   - **Criar nova biblioteca:** `http://127.0.0.1:8000/cadastro/`
   - **API REST:** `http://127.0.0.1:8000/api/`
   - **Admin Global (Superadmin):** `http://127.0.0.1:8000/admin/`

5. Comandos úteis do Docker:
   ```bash
   docker compose ps                              # Ver status dos containers
   docker compose logs -f web                     # Acompanhar logs da aplicação
   docker compose exec web python manage.py test  # Rodar testes no PostgreSQL
   docker compose down                            # Parar os containers
   ```

---

### Opção 2: Rodar Localmente sem Docker (SQLite)

Pré-requisitos: **Python 3.13** (ou 3.11+).

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell/CMD)
# source .venv/bin/activate     # Linux / macOS

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente (mantém DB_ENGINE=sqlite)
cp .env.example .env

# 4. Aplicar migrações e popular dados de demonstração
python manage.py migrate
python manage.py seed_demo

# 5. Iniciar o servidor de desenvolvimento
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/`.

---

## Contas de Demonstração (`seed_demo`)

| Usuário | Senha | Organização | Papel |
|---|---|---|---|
| `ana` | `admin1234` | Biblioteca Central | Administrador |
| `lucas` | `oper1234` | Biblioteca Central | Operador |
| `bruno` | `admin1234` | Biblioteca do Bairro | Administrador |
| `mariana` | `oper1234` | Biblioteca do Bairro | Operador |
| `superadmin` | `super1234` | *(Dono do SaaS — `/admin/`)* | Superusuário |

---

## Testes Automatizados

A suíte em `acervo/tests.py` possui **24 testes** cobrindo isolamento multi-tenant, cadastro de organizações, gestão de equipe, separação de superadmin, permissões por papel, dashboard, exportação CSV/PDF, regressão N+1 (`assertNumQueries`) e API REST:

```bash
# Local (SQLite)
python manage.py test -v 2

# Dentro do Docker (PostgreSQL)
docker compose exec web python manage.py test -v 2
```

---

## Tecnologias e Estrutura

- **Stack:** Python 3.13, Django 6.1, Django REST Framework, PostgreSQL 16 / SQLite, Chart.js, ReportLab, WhiteNoise, Gunicorn, Docker & Docker Compose.

```text
biblioteca/                configurações do projeto Django (settings, urls, wsgi)
core/                      app transversal multi-tenant (Organizacao, DaOrganizacao, Perfil,
                           permissões, cadastro/equipe e comando seed_demo)
acervo/                    app principal (models, forms, views, dashboard/CSV/PDF,
  ├── migrations/          migrações incluindo transição em 3 etapas da P1 -> P2
  ├── serializers.py       serializers DRF com validação por organização
  ├── api_views.py         ViewSets, ação /devolver/ e DashboardApi
  ├── api_urls.py          rotas /api/ via DefaultRouter
  ├── static/acervo/       CSS (home.css, style.css, auth.css), JS e capas SVG
  ├── templates/acervo/    templates HTML (home, login, cadastro, dashboard, CRUDs)
  └── tests.py             suíte com 24 testes automatizados
Dockerfile                 imagem de produção Python + Gunicorn + WhiteNoise
docker-compose.yml         orquestração PostgreSQL 16 + aplicação web
docker-entrypoint.sh       migrações automáticas e seed inicial no startup
.env.example               modelo de variáveis de ambiente
```

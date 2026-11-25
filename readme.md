# Sistema de Gerenciamento de Biblioteca (Mini-SaaS)

Projeto da disciplina **Laboratório de Programação Full Stack** (Universidade de Vassouras), evoluído da **P1** (MVP em Django puro) para a **P2** (Mini-SaaS multi-organização com perfis de acesso, dashboard analítico, exportação CSV/PDF, API REST com DRF e infraestrutura Docker + PostgreSQL).

## Pilares Implementados na P2

- **Multi-organização (`core`):** várias bibliotecas na mesma base com isolamento total via `Organizacao`, base abstrata `DaOrganizacao`, migração em 3 etapas preservando os dados da P1, unicidade por organização (`UniqueConstraint`) e filtros obrigatórios em todas as views, selects e API.
- **Perfis de Acesso:** autenticação obrigatória com `Perfil` (`Administrador` e `Operador`), restrição de exclusões, séries temporais e exportações ao papel `admin`, e tratamento seguro para usuários sem perfil.
- **Dashboard e Relatórios:** métricas calculadas no ORM (`aggregate`, `annotate`, `TruncMonth`), filtro por período validado (`PeriodoForm`), gráficos recomendados com Chart.js (linha para série temporal, barras horizontais para ranking e barras verticais/horizontais para distribuições — sem gráficos de pizza), exportação **CSV** (sanitizado contra formula injection) e **PDF** (ReportLab), além de auditoria N+1 e índices no banco.
- **API REST (DRF):** endpoints sob `/api/` (`livros`, `autores`, `exemplares`, `membros`, `emprestimos` com ação `/devolver/`, `reservas` e `dashboard`), serializers com campos explícitos, validações compartilhadas e isolamento multi-tenant.
- **Docker + PostgreSQL:** `Dockerfile`, `docker-compose.yml` e entrypoint automático com migrações e seed de demonstração.

## Tecnologias

- Python 3.13 + Django 6.1
- Django REST Framework
- PostgreSQL 16 (via Docker Compose) / SQLite (desenvolvimento local)
- Chart.js + ReportLab (PDF) + WhiteNoise + Gunicorn

## Como rodar com Docker (Recomendado)

```bash
cp .env.example .env
docker compose up --build
```

Acesse `http://127.0.0.1:8000/`. O entrypoint executa automaticamente as migrações e cria usuários de demonstração (`seed_demo`):

| Usuário | Senha | Organização | Papel |
|---|---|---|---|
| `admin_central` | `admin1234` | Organização padrão | Administrador |
| `operador_central` | `oper1234` | Organização padrão | Operador |
| `admin_bairro` | `admin1234` | Biblioteca do Bairro | Administrador |
| `operador_bairro` | `oper1234` | Biblioteca do Bairro | Operador |
| `admin` | `admin1234` | Organização padrão | Superusuário (`/admin/`) + Administrador |

## Como rodar localmente (sem Docker)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
cp .env.example .env            # mantém DB_ENGINE=sqlite
python manage.py migrate
python manage.py seed_demo      # opcional: cria usuários de demonstração
python manage.py runserver
```

## Testes Automatizados

```bash
python manage.py test
```

Cobertura em `acervo/tests.py`:
- Isolamento multi-tenant (listagens, 404 cruzado, selects de formulário, `UniqueConstraint` por organização)
- Permissões por papel (`admin` vs `operador`, proteção contra `RelatedObjectDoesNotExist` e `ProtectedError`)
- Dashboard, filtro por período, exportação CSV (sanitização) e exportação PDF
- Regressão N+1 com `assertNumQueries`
- API REST DRF (autenticação, CRUD, isolamento e ação de devolução)

## Estrutura

```text
biblioteca/          configurações do projeto Django (settings, urls)
core/                app transversal (Organizacao, DaOrganizacao, Perfil, permissões e seed_demo)
acervo/              app principal (models, forms, views, dashboard/CSV/PDF, serializers, api_views, tests)
Dockerfile           imagem da aplicação Python/Django
docker-compose.yml   orquestração PostgreSQL + aplicação web
```

#!/bin/sh
set -e

echo "Aplicando migrações no banco de dados..."
python manage.py migrate --noinput

if [ "${SEED_DEMO:-True}" = "True" ]; then
    echo "Verificando dados iniciais de demonstração..."
    python manage.py seed_demo
fi

exec "$@"

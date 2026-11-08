#!/usr/bin/env bash
# Script de build para Render.
set -o errexit

echo "=== Iniciando build de Render ==="

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Recopilar archivos est?ticos (CSS, im?genes, JS)
python manage.py collectstatic --no-input --verbosity 2

# Aplicar migraciones de base de datos
python manage.py migrate --no-input

echo "=== Build completado ==="

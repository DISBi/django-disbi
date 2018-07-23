#!/bin/bash
# Standard django setup.
python manage.py makemigrations
python manage.py makemigrations sulfolobus
python manage.py migrate
python manage.py collectstatic --noinput
# Populate database with sulfolobus data.
PGPASSWORD=$POSTGRES_PASSWORD psql -h db -d $POSTGRES_DB -U $POSTGRES_USER -f sulfolobus_data.sql
# Run server.
gunicorn example_disbi_project.wsgi --bind 0.0.0.0:8000

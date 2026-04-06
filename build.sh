#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
pip install gunicorn
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
import os
email = os.environ.get('SUPERUSER_EMAIL', 'admin@admin.com')
password = os.environ.get('SUPERUSER_PASSWORD', 'admin123')
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password, first_name='Admin', last_name='User')
    print('Superuser created')
else:
    print('Superuser already exists')
"

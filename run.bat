@echo off
echo ====================================================
echo Starting InvestIQ - Django Investment Research App
echo ====================================================

echo Installing dependencies...
pip install -r requirements.txt

echo Applying database migrations...
python manage.py migrate

echo Starting Django server...
python manage.py runserver

# Django-Setup

Setup a django rest project in 10mins.
(Svelte, React frontend implementation comming soon...)

This project is a fork of [this project](https://github.com/Vivify-Ideas/python-django-drf-boilerplate).

## Includes
- JSON Web Token authentication using [Simple JWT](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/)
- Social (FB + G+) signup/sigin
- Password reset endpoints
- User model with profile picture field using Easy Thumbnails
- Files management (thumbnails generated automatically for images)
- Swagger API docs out-of-the-box
- PostGres or MySQL your choice 🤷‍♀️

## API Docs

API documentation is automatically generated using Swagger. You can view documention by visiting at these paths

```bash
swagger/
redoc/
```


## Local Development without Docker

### Install

```bash
# note: this is bash running on windows env/scripts/activate might be env/bin/activate on a full linux environment

git clone git@github.com:KingWilliamsGPT/django-setup.git

cd django-setup

# create virtual environment
python3 -m venv env

# activate virtual environment
source env/scripts/activate

# create configuration file
cp .env.example .env

# install requirements
# sudo apt-get install python3-dev default-libmysqlclient-dev build-essential # might need this
pip install -r requirements/dev.txt

python manage.py migrate
python manage.py collectstatic --noinput
```

### Run dev server

This will run server on [http://localhost:8000](http://localhost:8000)

```bash
python manage.py runserver
```

### Create superuser

If you want, you can create initial super-user with next commad:

```bash
python manage.py createsuperuser
```

### Setup database
The default database is sqlite (unsuitable for production), to switch to MySQL, ie. after renaming `.env.example` to `.env`, follow the following steps.

At your .env file
```bash
# Changed to False
USE_DEFAULT_BACKEND=False

# wil use sqlite 
USE_DEFAULT_BACKEND=True

# set to either mysql or postgres
ALT_BACKEND=mysql

# Set these according to your database server
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
```

#### Ensure mysqlclient is installed
```bash
# activate virtual environment first
pip install mysqlclient
```

That should do it.


### With Docker
Comming soon...


## Project Structure
[check here](./project_tree.md)
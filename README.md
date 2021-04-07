# Eng-IT

## How to debug

```bash
$ export NEWSAPI_KEY="<NEWSAPI_KEY>"
$ export GOOGLE_APPLICATION_CREDENTIALS="<path to secret json>"
$ export DJANGO_SETTINGS_MODULE=config.settings.base
$ python3.6 -m venv venv
$ . venv/bin/activate
$ pip install -r ./requirements/base.txt
$ python ./manage.py migrate
$ python ./manage.py runserver
```

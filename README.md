![Foodgram workflow](https://github.com/RabcriN/foodgram-project-react/actions/workflows/main.yml/badge.svg)

Сайт доступен по адресу http://84.201.160.143/ 

# Проект Foodgram

### Описание
Проект **Foodgram** является сайтом для любителей кулинарии. Здесь вы можете создавать рецепты, прикрепляя к ним картинки, смотреть рецепты других пользователей и добавлять их в избранное. Вы можете подписаться на понравившегося автора и видеть все его обновления. Можно добавлять рецепты в корзину, при этом можно будет получить файл, с перечнем всех необходимых ингредиентов и их суммарным количеством.

### Пользовательские роли
* **Аноним** — может просматривать рецепты.
* **Аутентифицированный пользователь** — может, как и Аноним, читать всё. дополнительно он может публиковать рецепты, добавлять рецепты в избранное и в корзину, подписываться на понравившихся авторов.
* **Администратор** — полные права на управление всем контентом проекта. Может назначать роли пользователям.
* **Суперюзер Django** — обладет правами администратора.


### Как запустить проект:

Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/RabcriN/foodgram-project-react
```

Добавить в https://github.com/<your_name>/foodgram-project-react/settings/secrets/actions
следующие ключи:
```

SECRET_KEY - Секретный ключ Вашего проекта для settings.py.

DEBUG - Выбрать режим разработки или отладки (по умолчанию False).
Варианты значений для "DEBUG": True values are "y", "yes", "t", "true", "on" and "1". False values are "n", "no", "f", "false", "off" and "0".
 
DB_ENGINE- Параметр указывает на используемый движок для доступа к БД.
По умолчанию используется Postgres.

DB_NAME - Имя базы данных.

POSTGRES_USER - Имя учётной записи для суперпользователя в Postgres.

POSTGRES_PASSWORD - Пароль для суперпользователя в Postgres.

DB_HOST - IP-адрес удаленной БД.
По умолчанию БД берётся из docker-контейнера под названием "db".

DB_PORT - Порт для подключения к БД.
По умолчанию для Postgres - 5432
```

### Проект автоматически разворачивается по адресу 84.201.160.143 при внесении изменений и команде git push 
### Переходим на сервер и

Выполняем миграции:
```
sudo docker-compose exec backend python manage.py migrate
```
Создаём суперюзера:
```
sudo docker-compose exec backend python manage.py createsuperuser
```
Собираем статику:

```
sudo docker-compose exec backend python manage.py collectstatic --no-input 
```

Админка доступна по адресу:

```
http://84.201.160.143/admin/
```
### Если используете Google Chrome и админка отображается некорректно:

Перезагрузите страницу, игнорируя кэшированное содержимое.

```
Ctrl + F5 (Shift + F5) или Ctrl + Shift + R
```

Полная документация доступна по адресу:

```
http://84.201.160.143/api/docs/
```

Стек технологий:
- Python 3.7 (https://docs.python.org/3/whatsnew/3.7.html)
- Django 3.2 (https://docs.djangoproject.com/en/3.2/)
- DRF (https://www.django-rest-framework.org/)
- Docker / Docker-compose (https://www.docker.com/)
- Nginx (http://nginx.org/en/docs/)
- Postgresql (https://www.postgresql.org/docs/)
- GitHub Actions workflows (https://docs.github.com/en/actions/using-workflows)

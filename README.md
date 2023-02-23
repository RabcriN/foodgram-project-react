![Foodgram workflow](https://github.com/RabcriN/foodgram-project-react/actions/workflows/main.yml/badge.svg)

Проект доступен по адресу http://84.201.160.143/ 

# Проект Foodgram 

### Описание
Проект **Foodgram** является сайтом для любителей кулинарии. Здесь вы можете создавать рецепты, прикрепляя к ним картинки, смотреть рецепты других пользователей и добавлять их в избранное. Вы можете подписаться на понравившегося автора и видеть все его обновления. Можно добавлять рецепты в корзину, при этом можно будет получить файл, с перечнем всех необходимых ингредиентов и их суммарным количеством.

### Пользовательские роли
* **Аноним** — может просматривать рецепты.
* **Аутентифицированный пользователь** — может, как и Аноним, читать всё. дополнительно он может публиковать рецепты, добавлять рецепты в избранное и в корзину, подписываться на понравившихся авторов.
* **Администратор** — полные права на управление всем контентом проекта. Может назначать роли пользователям.
* **Суперюзер Django** — обладет правами администратора.


### Как запустить проект:
Клонировать репозиторий:
```
git clone https://github.com/RabcriN/foodgram-project-react
```
и выполнить 
```
docker-compose up
```

Админка доступна по адресу:

http://84.201.160.143/admin/

Полная документация доступна по адресу:

http://84.201.160.143/api/docs/


Стек технологий:
- Python 3.7 (https://docs.python.org/3/whatsnew/3.7.html)
- Django 3.2 (https://docs.djangoproject.com/en/3.2/)
- DRF (https://www.django-rest-framework.org/)
- Docker / Docker-compose (https://www.docker.com/)
- Nginx (http://nginx.org/en/docs/)
- Postgresql (https://www.postgresql.org/docs/)
- GitHub Actions workflows (https://docs.github.com/en/actions/using-workflows)

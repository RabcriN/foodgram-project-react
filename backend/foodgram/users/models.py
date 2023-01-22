from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

ADMIN = 'Admin'
AUTH = 'Auth'
GUEST = 'Guest'

CHOICES = (
    (ADMIN, 'Администратор'),
    (AUTH, 'Авторизованный'),
    (GUEST, 'Гость'),
)


class User(AbstractUser):
    username = models.CharField(
        validators=[
            RegexValidator(r'^[\w.@+-]+\Z', 'Enter a valid username.'),
        ],
        max_length=150,
        verbose_name='Юзернейм',
        blank=False,
    )
    email = models.EmailField(
        verbose_name='Email',
        max_length=245,
        blank=False,
        unique=True,
    )
    first_name = models.CharField(
        verbose_name='Имя', max_length=150, blank=False,
    )
    last_name = models.CharField('Фамилия', max_length=150, blank=False,)
    subscription = models.ManyToManyField(
        'User',
        blank=True,
        related_name='subscripted_by'
    )
    role = models.CharField(
        verbose_name='Статус',
        choices=CHOICES,
        default=GUEST,
        max_length=50,
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [
        'id', 'username', 'first_name', 'last_name',
    ]

    def __str__(self):
        return self.username

    class Meta:
        ordering = ('email',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    @property
    def is_admin(self):
        return self.role == ADMIN or self.is_staff or self.is_superuser

    @property
    def is_auth(self):
        return self.role == AUTH

    @property
    def is_guest(self):
        return self.role == GUEST

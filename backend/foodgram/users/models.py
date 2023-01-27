from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Exists, OuterRef

ADMIN = 'Admin'
AUTH = 'Auth'
GUEST = 'Guest'

CHOICES = (
    (ADMIN, 'Администратор'),
    (AUTH, 'Авторизованный'),
    (GUEST, 'Гость'),
)


class UserQuerySet(models.QuerySet):
    def add_user_annotation(self, user_id):
        return self.annotate(
            is_subscribed=Exists(
                User.subscription.through.objects.filter(
                    to_user__pk=OuterRef('pk'),
                    from_user_id=user_id
                )
            )
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
        related_name='subscripted_by',
        verbose_name='Подписки'
    )
    role = models.CharField(
        verbose_name='Статус',
        choices=CHOICES,
        default=GUEST,
        max_length=50,
    )
    objects = UserQuerySet.as_manager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [
        'id', 'username', 'first_name', 'last_name',
    ]

    def __str__(self):
        return self.username

    class Meta:
        ordering = ('email',)
        verbose_name = 'Пользователя'
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

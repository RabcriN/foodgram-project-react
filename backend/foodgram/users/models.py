from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Exists, OuterRef

from .managers import CustomUserManager

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
                UserSubscription.objects.filter(
                    subscribe_to=OuterRef('pk'),
                    user_id=user_id
                )
            )
        )


class UserManager(CustomUserManager):
    def get_queryset(self):
        return UserQuerySet(
            model=self.model,
            using=self._db,
            hints=self._hints
        )


MyCustomManager = UserManager.from_queryset(UserQuerySet)


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
        through='UserSubscription',
        related_name='user_subscription',
        verbose_name='Подписан на'
    )
    role = models.CharField(
        verbose_name='Статус',
        choices=CHOICES,
        default=GUEST,
        max_length=50,
    )
    objects = MyCustomManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [
        'username', 'first_name', 'last_name',
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


class UserSubscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Пользователь',
    )
    subscribe_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Подписаться на',
        related_name='usersubscription_subscribe_to',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

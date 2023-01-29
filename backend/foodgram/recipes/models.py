from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Exists, OuterRef
from users.models import User


class Tag(models.Model):
    name = models.CharField(
        verbose_name='Название',
        max_length=200,
        blank=False,
    )
    color = models.CharField(
        verbose_name='Цвет в HEX',
        max_length=7,
        blank=False,
        null=True,
    )
    slug = models.SlugField(
        validators=[
            RegexValidator(r'^[-a-zA-Z0-9_]+$', 'Enter a valid slug.'),
        ],
        max_length=200,
        verbose_name='Слаг',
        blank=False,
        null=True,
        unique=True,
    )

    def __str__(self):
        return self.name[:20]

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'


class Ingredient(models.Model):
    name = models.CharField(
        verbose_name='Название',
        max_length=200,
        blank=False,
    )
    measurement_unit = models.CharField(
        verbose_name='Единицы измерения',
        max_length=200,
        blank=False,
    )

    def __str__(self):
        return self.name[:20]

    class Meta:
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингридиенты'


class RecipeQuerySet(models.QuerySet):
    def add_user_annotation(self, user_id):
        return self.annotate(
            is_favorited=Exists(
                Recipe.favorites.through.objects.filter(
                    recipe__pk=OuterRef('pk'),
                    user_id=user_id,
                )
            ),
            is_in_shopping_cart=Exists(
                Recipe.shopping_carts.through.objects.filter(
                    recipe__pk=OuterRef('pk'),
                    user_id=user_id
                )
            )
        )


class Recipe(models.Model):
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        verbose_name='Теги рецепта',
        related_name='recipe_tags',
    )

    author = models.ForeignKey(
        User,
        verbose_name='Автор рецепта',
        on_delete=models.CASCADE,
        related_name='recipe_author',
    )

    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientsAmount',
        blank=False,
        verbose_name='Ингридиенты рецепта',
        related_name='recipe_ingridients',
    )
    favorites = models.ManyToManyField(
        User,
        blank=True,
        related_name='favorite_recipes',
        verbose_name='В избранном у'
    )
    shopping_carts = models.ManyToManyField(
        User,
        blank=True,
        related_name='in_shopping_cart_recipes',
        verbose_name='В корзине у'
    )
    name = models.CharField(
        verbose_name='Название',
        max_length=200,
        blank=False,
    )
    image = models.ImageField(blank=True, verbose_name='Картинка')
    text = models.TextField(verbose_name='Текст рецепта')
    cooking_time = models.IntegerField(verbose_name='Время приготовления',)
    objects = RecipeQuerySet.as_manager()

    def __str__(self):
        return self.name[:20]

    class Meta:
        ordering = ['id']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'


class IngredientsAmount(models.Model):

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингридиент',
    )
    amount = models.IntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
        ],
        verbose_name='Количество',
    )


class ShoppingCart(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.SET_NULL, null=True,)

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзина'

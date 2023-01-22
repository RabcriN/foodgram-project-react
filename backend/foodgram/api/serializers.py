from django.core.validators import RegexValidator
from django.db import IntegrityError, transaction
from django.http import Http404
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import Ingredient, IngredientsAmount, Recipe, Tag
from users.models import User


class UserSerializer(serializers.ModelSerializer):
    """Сериализация пользователей"""
    email = serializers.EmailField(required=True)
    username = serializers.CharField(
        validators=[
            RegexValidator(r'^[\w.@+-]+\Z', 'Enter a valid username.'),
        ],
        max_length=150, required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    is_subscribed = serializers.SerializerMethodField('subscription')

    password = serializers.CharField(
        style={'input_type': 'password'},
        max_length=150,
        write_only=True
    )

    def subscription(self, obj):
        user = obj
        if user.is_authenticated is False:
            return False
        return user.subscription.filter(pk=obj.pk).exists()

    def validate_email(self, value):
        lower_email = value.lower()
        if User.objects.filter(email__iexact=lower_email).exists():
            raise serializers.ValidationError(
                f'The User with email {lower_email} already exists!'
            )
        return lower_email

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'password',
        )


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change endpoint."""

    new_password = serializers.CharField(
        max_length=128, write_only=True, required=True
    )
    current_password = serializers.CharField(
        max_length=128, write_only=True, required=True
    )

    def validate_current_password(self, value):
        user = self.context['user']
        if not user.check_password(value):
            raise serializers.ValidationError(
                'Your current password was entered incorrectly.'
                ' Please enter it again.'
            )
        return value

    def save(self, **kwargs):
        password = self.validated_data['new_password']
        user = self.context['user']
        user.set_password(password)
        user.save()
        return user


class TagSerializer(serializers.ModelSerializer):
    """Сериализация тегов"""

    class Meta:
        model = Tag
        fields = (
            'id', 'name', 'color', 'slug',
        )


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализация ингридиентов"""
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Ingredient
        fields = (
            'id', 'name', 'measurement_unit',
        )


class IngredientsAmountSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientsAmount
        fields = (
            'id', 'name', 'measurement_unit', 'amount',
        )


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализация чтения рецептов"""

    id = serializers.IntegerField(read_only=True)
    tags = TagSerializer(many=True)
    author = UserSerializer()
    ingredients = IngredientsAmountSerializer(
        source='ingredientsamount_set',
        many=True
    )
    is_favorited = serializers.SerializerMethodField('favorited')
    is_in_shopping_cart = serializers.SerializerMethodField('shopping_cart')
    name = serializers.CharField(max_length=200, allow_blank=False)
    image = Base64ImageField(required=False)
    text = serializers.CharField()
    cooking_time = serializers.IntegerField()

    def favorited(self, obj):
        request = self.context.get('request', None)
        if not request:
            return False
        user = request.user
        if not request.user.is_authenticated:
            return False
        return user.favorite_recipes.filter(pk=obj.pk).exists()

    def shopping_cart(self, obj):
        request = self.context.get('request', None)
        if not request:
            return False
        user = request.user
        if not request.user.is_authenticated:
            return False
        return user.in_shopping_cart_recipes.filter(pk=obj.pk).exists()

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError(
                'Cooking time have to be more than 1 minutes!'
            )
        return value

    class Meta:
        model = Recipe
        fields = (
            '__all__'
        )


class TestIngredientsAmountSerializer(serializers.Serializer):
    id = serializers.CharField(source='ingredient.id')
    amount = serializers.CharField(source='ingredient.amount')


class WriteRecipeSerializer(serializers.ModelSerializer):
    """Сериализация записи рецепта"""
    ingredients = TestIngredientsAmountSerializer(
        many=True,
        required=True,
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        read_only=False,
        required=True,
    )
    image = Base64ImageField(required=False)
    name = serializers.CharField(
        max_length=200,
        allow_blank=False,
        required=True,
    )
    text = serializers.CharField(required=True,)
    cooking_time = serializers.IntegerField(required=True,)
    author = serializers.CharField(required=False)

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError(
                'Cooking time have to be more than 1 minutes!'
            )
        return value

    def create(self, validated_data):
        try:
            with transaction.atomic():
                ingredients_data = validated_data.pop('ingredients')
                recipe = super().create(validated_data)
                recipe.save()
                for ingredient in ingredients_data:
                    amount = ingredient['ingredient']['amount']
                    ingredient_id = ingredient['ingredient']['id']
                    IngredientsAmount.objects.create(
                        recipe=recipe,
                        ingredient_id=ingredient_id,
                        amount=amount,
                    )
                    return recipe
        except IntegrityError:
            raise Http404()

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        instance.ingredients.clear()
        for ingredient_data in ingredients_data:
            IngredientsAmount.objects.create(
                recipe=instance,
                ingredient=Ingredient.objects.get(
                    pk=ingredient_data['ingredient']['id']
                ),
                amount=ingredient_data['ingredient']['amount']
            )
        return instance

    def to_representation(self, instance):
        serializer = RecipeSerializer(instance)
        return serializer.data

    class Meta:
        model = Recipe
        fields = (
            '__all__'
        )


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Добавление рецепта в список покупок"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    image = Base64ImageField(required=False)
    cooking_time = serializers.IntegerField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'image', 'cooking_time',
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализация подписок"""
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    def get_is_subscribed(self, obj):
        request = self.context.get('request', None)
        user = request.user
        return user.subscription.filter(pk=obj.pk).exists()

    def get_recipes(self, obj):
        if self.context["recipes_limit"]:
            limit = int(self.context["recipes_limit"])
            queryset = obj.recipe_author.all()[:limit]
            return ShoppingCartSerializer(queryset, many=True).data
        queryset = obj.recipe_author.all()
        return ShoppingCartSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipe_author.all().count()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )
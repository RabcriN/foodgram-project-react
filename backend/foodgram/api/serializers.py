from django.db import IntegrityError
from django.db.models import Prefetch
from django.http import Http404
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (FavorRecipe, Ingredient, IngredientsAmount, Recipe,
                            ShoppingCart, Tag)
from rest_framework import serializers
from users.models import User, UserSubscription


class UserSerializer(serializers.ModelSerializer):
    """Сериализация пользователей"""

    is_subscribed = serializers.BooleanField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        max_length=150,
        write_only=True
    )

    def create(self, validated_data):
        user = User(
            last_name=validated_data['last_name'],
            first_name=validated_data['first_name'],
            email=validated_data['email'],
            username=validated_data['username']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

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
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализация ингридиентов"""

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

    tags = TagSerializer(many=True)
    author = UserSerializer()
    ingredients = IngredientsAmountSerializer(
        source='ingredientsamount_set',
        many=True
    )
    is_favorited = serializers.BooleanField()
    is_in_shopping_cart = serializers.BooleanField()

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError(
                'Cooking time have to be more than 1 minutes!'
            )
        return value

    class Meta:
        model = Recipe
        exclude = ('favorites', 'shopping_carts',)


class WriteIngredientsAmountSerializer(serializers.Serializer):
    id = serializers.CharField(source='ingredient.id')
    amount = serializers.CharField(source='ingredient.amount')


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализация записи рецепта"""
    ingredients = WriteIngredientsAmountSerializer(
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

    @staticmethod
    def _link_recipe_ingridients(recipe, ingredients_data):
        objs = []
        for ingredient in ingredients_data:
            amount = ingredient['ingredient']['amount']
            ingredient_id = ingredient['ingredient']['id']
            objs.append(IngredientsAmount(
                recipe=recipe,
                ingredient_id=ingredient_id,
                amount=amount,
            ))
        try:
            IngredientsAmount.objects.bulk_create(objs)
        except IntegrityError:
            raise Http404()

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        recipe = super().create(validated_data)
        recipe.save()
        self._link_recipe_ingridients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        instance.ingredients.clear()
        self._link_recipe_ingridients(instance, ingredients_data)
        return instance

    def to_representation(self, instance):
        user = self.context['request'].user
        recipe = Recipe.objects.add_user_annotation(user.id).prefetch_related(
            Prefetch(
                'author',
                queryset=User.objects.add_user_annotation(user.id)
            )
        ).get(id=instance.id)
        serializer = RecipeSerializer(recipe, context=self.context)
        return serializer.data

    class Meta:
        model = Recipe
        fields = (
            '__all__'
        )


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализация отображения рецепта"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    image = Base64ImageField(required=False)
    cooking_time = serializers.IntegerField()

    def create(self, validated_data):
        if FavorRecipe.objects.filter(
            user=validated_data['user'],
            recipe=validated_data['recipe']
        ).exists():
            raise serializers.ValidationError("Already favorited.")
        return super().create(validated_data)

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'image', 'cooking_time',
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализация подписок"""
    is_subscribed = serializers.BooleanField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    def get_recipes(self, obj):
        if ('recipes_limit' in self.context
           and self.context['recipes_limit'] is not None):
            limit = int(self.context['recipes_limit'])
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


class FavorSerializer(serializers.ModelSerializer):
    """Сериализация добавления рецепта в избранное"""

    def create(self, validated_data):
        if FavorRecipe.objects.filter(
            user=validated_data['user'],
            recipe=validated_data['recipe']
        ).exists():
            raise serializers.ValidationError("Already favorited.")
        return super().create(validated_data)

    class Meta:
        model = FavorRecipe
        fields = '__all__'


class ShoppingSerializer(serializers.ModelSerializer):
    """Сериализация добавления рецепта в корзину"""
    def create(self, validated_data):
        if ShoppingCart.objects.filter(
            user=validated_data['user'],
            recipe=validated_data['recipe']
        ).exists():
            raise serializers.ValidationError("Already in shopping cart.")
        return super().create(validated_data)

    class Meta:
        model = ShoppingCart
        fields = '__all__'


class SubSerializer(serializers.ModelSerializer):
    """Сериализация создания подписки"""

    def create(self, validated_data):
        user = validated_data['user']
        subscribe_to = validated_data['subscribe_to']
        if UserSubscription.objects.filter(
            user=user,
            subscribe_to=subscribe_to
        ).exists():
            raise serializers.ValidationError('Already subscribed.')
        if user == subscribe_to:
            raise serializers.ValidationError(
                "You can't subscribe to yourself"
            )
        return super().create(validated_data)

    class Meta:
        model = UserSubscription
        fields = '__all__'

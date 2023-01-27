from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from recipes.models import Ingredient, IngredientsAmount, Recipe, Tag
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from users.models import User

from .pagination import PageAndLimitPagination
from .serializers import (ChangePasswordSerializer, IngredientSerializer,
                          RecipeSerializer, SubscriptionSerializer,
                          TagSerializer, UserSerializer, WriteRecipeSerializer)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['get', 'post', 'delete']
    pagination_class = PageAndLimitPagination
    filter_backends = (SearchFilter,)
    search_fields = ('username',)
    lookup_field = 'id'

    def get_permissions(self):
        if self.action in ['list', 'create']:
            permission_classes = [AllowAny, ]
        else:
            permission_classes = [AllowAny, ]
        return [permission() for permission in permission_classes]

    @action(
        detail=False,
        methods=('GET',),
        url_path='me',
        permission_classes=(IsAuthenticated,),
    )
    def me(self, request):
        """Профайл пользователя."""
        serializer = UserSerializer(
            request.user,
            context={
                'request': request
            }
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=('POST',),
        url_path='set_password',
        permission_classes=(AllowAny,),
    )
    def set_password(self, request):
        """Смена пароля."""
        user = request.user
        serializer = ChangePasswordSerializer(
            user, data=request.data, many=False,
            context={'user': request.user}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('GET',),
        url_path='subscriptions',
        permission_classes=(AllowAny,),
        serializer_class=SubscriptionSerializer,
    )
    def subscriptions(self, request):
        """Пользователи, на которых подписан текущий пользователь"""
        recipes_limit = request.GET.get('recipes_limit', None)
        user = request.user
        queryset = user.subscription.all()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page,
            many=True,
            context={
                'request': request,
                'recipes_limit': recipes_limit,
            }
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=('POST', 'DELETE',),
        url_path='subscribe',
        permission_classes=(AllowAny,),
        serializer_class=SubscriptionSerializer,
    )
    def subscribe(self, request, id):
        user = request.user
        subscribe_to = get_object_or_404(User, id=self.kwargs.get('id'))
        if request.method == 'POST':
            if user == subscribe_to:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            if user.subscription.filter(pk=subscribe_to.id).exists():
                return Response(status=status.HTTP_400_BAD_REQUEST)
            user.subscription.add(subscribe_to)
            return Response(status=status.HTTP_200_OK)
        if request.method == 'DELETE':
            if user.subscription.filter(pk=subscribe_to.id).exists():
                user.subscription.remove(subscribe_to)
                return Response(status=status.HTTP_200_OK)
            return Response(status=status.HTTP_400_BAD_REQUEST)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    permission_classes = (
        AllowAny,
    )
    serializer_class = TagSerializer
    http_method_names = ['get', ]
    pagination_class = None
    lookup_field = "id"


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (
        AllowAny,
    )
    http_method_names = ['get', ]
    pagination_class = None
    lookup_field = "id"

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        keyword = self.request.GET.get('name',)
        if keyword:
            queryset = queryset.filter(name__istartswith=keyword)
        return queryset


class RecipesViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = PageAndLimitPagination
    http_method_names = ['post', 'get', 'patch', 'delete', ]
    lookup_field = "id"

    def get_permissions(self):
        if self.action in ['create', 'delete']:
            permission_classes = [AllowAny, ]
        if self.action in ['delete', 'update', 'perform_update']:
            permission_classes = [AllowAny, ]
        else:
            permission_classes = [AllowAny, ]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = Recipe.objects.all()
        kwargs = {
            'author': self.request.GET.get('author', ''),
            'tags': self.request.query_params.getlist('tags'),
            'is_favorited': self.request.GET.get('is_favorited'),
            'is_in_shopping_cart': self.request.GET.get('is_in_shopping_cart'),
        }
        filter_kwargs = {}
        if (
            (
                ('is_favorited' in kwargs and kwargs['is_favorited'])
                or (
                    'is_in_shopping_cart' in kwargs
                    and kwargs['is_in_shopping_cart']
                )
            )
            and self.request.user.id is None
        ):
            return []
        if 'author' in kwargs and kwargs['author']:
            filter_kwargs['author'] = kwargs['author']
        if 'tags' in kwargs and kwargs['tags']:
            filter_kwargs['tags__slug__in'] = kwargs['tags']
        if (
            'is_favorited' in kwargs and kwargs['is_favorited']
        ):
            filter_kwargs['is_favorited'] = self.request.user.id
        if (
            'is_in_shopping_cart' in kwargs and kwargs['is_in_shopping_cart']
        ):
            filter_kwargs['is_in_shopping_cart'] = self.request.user.id
        return queryset.filter(**filter_kwargs)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', ]:
            return WriteRecipeSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        if not serializer.is_valid():
            raise ValidationError(
                serializer.errors,
                status=status.HTTP_404_NOT_FOUND
            )
        serializer.save(author=self.request.user)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        user = request.user
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('id'))
        author = recipe.author
        if not user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        if author != user:
            return Response(status=status.HTTP_403_FORBIDDEN)

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('id'))
        author = recipe.author
        if not user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        if author == user:
            Recipe.delete(recipe)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_403_FORBIDDEN)

    @action(
        detail=False,
        methods=("GET",),
        url_path="download_shopping_cart",
        permission_classes=(AllowAny,),
    )
    def download_shopping_cart(self, request):
        """Скачать файл со списком покупок."""
        ingredients = IngredientsAmount.objects.filter(
            recipe__is_in_shopping_cart__username=request.user
        ).values('ingredient__name', 'ingredient__measurement_unit').annotate(
            total_amount=Sum('amount')
        )
        text = ''
        for ingredient in ingredients:
            text += (
                f"{ingredient['ingredient__name']} "
                f"({ingredient['ingredient__measurement_unit']}) - "
                f"{ingredient['total_amount']}\n"
            )
        filename = 'products.txt'
        response = HttpResponse(text, content_type='text/plain')
        response['Content-Disposition'] = f'attachement; filename={filename}'
        return response

    @action(
        detail=True,
        methods=('POST', 'DELETE',),
        url_path='favorite',
        permission_classes=(AllowAny,),
    )
    def favorite(self, request, id):
        user = request.user
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('id'))
        if request.method == 'POST':
            if recipe in user.favorite_recipes.all():
                return Response(status=status.HTTP_400_BAD_REQUEST)
            recipe.is_favorited.add(user)
            return Response(status=status.HTTP_200_OK)
        if request.method == 'DELETE':
            if recipe not in user.favorite_recipes.all():
                return Response(status=status.HTTP_400_BAD_REQUEST)
            recipe.is_favorited.remove(user)
            return Response(status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=('POST', 'DELETE',),
        url_path='shopping_cart',
        permission_classes=(AllowAny,),
    )
    def shopping_cart(self, request, id):
        user = request.user
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('id'))
        if request.method == 'POST':
            if recipe in user.in_shopping_cart_recipes.all():
                return Response(status=status.HTTP_400_BAD_REQUEST)
            recipe.is_in_shopping_cart.add(user)
            return Response(status=status.HTTP_200_OK)
        if request.method == 'DELETE':
            if recipe not in user.in_shopping_cart_recipes.all():
                return Response(status=status.HTTP_400_BAD_REQUEST)
            recipe.is_in_shopping_cart.remove(user)
            return Response(status=status.HTTP_200_OK)


class ShoppingCartViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    http_method_names = ['post', 'delete', ]
    pagination_class = None

    def perform_create(self, serializer):
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('recipes_id'))
        user = get_object_or_404(User, id=self.kwargs.get('user_id'))
        if user not in recipe.is_in_shopping_cart.all():
            recipe.is_in_shopping_cart.add(user)
            return Response(status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('recipes_id'))
        user = get_object_or_404(User, id=self.kwargs.get('user_id'))
        if user in recipe.is_in_shopping_cart.all():
            recipe.is_in_shopping_cart.remove(user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    http_method_names = ['post', 'delete', ]
    pagination_class = None
    lookup_field = "id"

    def perform_create(self, serializer):
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('recipes_id'))
        user = get_object_or_404(User, id=self.kwargs.get('user_id'))
        if user not in recipe.is_favorited.all():
            recipe.is_favorited.add(user)
            return Response(status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('recipes_id'))
        user = get_object_or_404(User, id=self.kwargs.get('user_id'))
        if user in recipe.is_favorited.all():
            recipe.is_favorited.remove(user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

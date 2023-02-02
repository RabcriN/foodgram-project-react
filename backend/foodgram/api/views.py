from django.db.models import Prefetch, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from recipes.models import (FavorRecipe, Ingredient, IngredientsAmount, Recipe,
                            Tag)
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import (AllowAny, IsAdminUser, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from users.models import User, UserSubscription

from .filters import RecipeFilter
from .pagination import PageAndLimitPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (ChangePasswordSerializer, FavorSerializer,
                          IngredientSerializer, RecipeSerializer,
                          RecipeWriteSerializer, ShoppingCartSerializer,
                          ShoppingSerializer, SubscriptionSerializer,
                          SubSerializer, TagSerializer, UserSerializer)


class UserViewSet(viewsets.ModelViewSet):
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
            permission_classes = [IsAuthenticated, ]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = User.objects.add_user_annotation(self.request.user.id)
        return queryset

    @action(
        detail=False,
        methods=('GET',),
        url_path='me',
        authentication_classes=[TokenAuthentication, ],
        permission_classes=(IsAuthenticated,),
    )
    def me(self, request):
        """Профайл пользователя."""
        user = request.user
        user.is_subscribed = False
        serializer = UserSerializer(
            user,
            context={
                'request': request
            }
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=('POST',),
        url_path='set_password',
        permission_classes=(IsAuthenticated, IsAdminUser),
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
        permission_classes=(IsAuthenticated,),
        serializer_class=SubscriptionSerializer,
    )
    def subscriptions(self, request):
        """Пользователи, на которых подписан текущий пользователь"""
        recipes_limit = request.GET.get('recipes_limit', None)
        user = request.user
        queryset = user.subscription.add_user_annotation(user.id).all()
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
        methods=('POST',),
        url_path='subscribe',
        permission_classes=(IsAuthenticated,),
        serializer_class=UserSerializer,
    )
    def subscribe(self, request, id):
        """Текущий пользователь подписывается на пользователя с id"""
        user = request.user
        recipes_limit = request.GET.get('recipes_limit', None)
        subscribe_to = self.get_object()
        serializer = SubSerializer(
            data={
                'user': user.id,
                'subscribe_to': subscribe_to.id,
            },
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        user.subscription.add(subscribe_to)
        subscribe_to = (
            User.objects.add_user_annotation(user).get(
                id=subscribe_to.id
            )
        )
        serializer = SubscriptionSerializer(
            subscribe_to,
            context={
                'recipes_limit': recipes_limit
            }
        )
        return Response(
            data=serializer.data, status=status.HTTP_201_CREATED
        )

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id):
        """Текущий пользователь удаляет подписку на пользователя с id"""
        user = request.user
        subscribe_to = self.get_object()
        if not UserSubscription.objects.filter(
            user=user,
            subscribe_to=subscribe_to
        ).exists():
            return Response(
                {'You are not subscribed to this user'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.subscription.remove(subscribe_to)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    permission_classes = (
        AllowAny,
    )
    serializer_class = TagSerializer
    http_method_names = ['get', ]
    pagination_class = None
    lookup_field = 'id'


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (
        AllowAny,
    )
    http_method_names = ['get', ]
    pagination_class = None
    lookup_field = 'id'

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        keyword = self.request.GET.get('name',)
        if keyword:
            queryset = queryset.filter(name__istartswith=keyword)
        return queryset


class RecipesViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    permission_classes = (
        IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly,
    )
    pagination_class = PageAndLimitPagination
    filterset_class = (RecipeFilter)
    http_method_names = ['post', 'get', 'patch', 'delete', ]
    lookup_field = 'id'

    def get_queryset(self):
        queryset = Recipe.objects.add_user_annotation(
            self.request.user.id
        ).prefetch_related(
            Prefetch(
                'author',
                queryset=User.objects.add_user_annotation(self.request.user.id)
            )
        )
        return queryset

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', ]:
            return RecipeWriteSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        user = self.request.user
        user = User.objects.add_user_annotation(user).get(id=user.id)
        serializer.save(
            author=user,
        )

    @action(
        detail=False,
        methods=("GET",),
        url_path="download_shopping_cart",
        permission_classes=(IsAuthenticated,),
    )
    def download_shopping_cart(self, request):
        """Скачать файл со списком покупок."""
        ingredients = IngredientsAmount.objects.filter(
            recipe__shopping_carts__username=request.user
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
        methods=('POST',),
        url_path='favorite',
        permission_classes=(IsAuthenticated,),
        serializer_class=(ShoppingCartSerializer,)
    )
    def favorite(self, request, id):
        """Текущий пользователь добавляет рецепт в избранное по id"""
        user = request.user
        recipe = self.get_object()
        serializer = FavorSerializer(
            data={
                'recipe': recipe.id,
                'user': user.id,
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        recipe.favorites.add(user)
        serializer = ShoppingCartSerializer(recipe)
        return Response(
            data=serializer.data, status=status.HTTP_201_CREATED
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, id):
        """Текущий пользователь удаляет рецепт из избранного по id"""
        user = request.user
        recipe = self.get_object()
        if not FavorRecipe.objects.filter(user=user, recipe=recipe).exists():
            return Response(
                {'This recipe is not in your favorites'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Просто убрать проверку и выполнить
        # User.favorites.filter(recipe_id=id).all().delete()
        # Мы тоже не можем, т.к по ТЗ мы должны возвращать:
        # "400 Ошибка удаления из избранного (Например, когда
        # рецепта там не было)". Причём с описанием ошибки:
        # "RESPONSE SCHEMA: application/json
        # errors string Описание ошибки".
        # И так во всех методах delete.
        recipe.favorites.remove(user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('POST',),
        url_path='shopping_cart',
        permission_classes=(IsAuthenticated,),
    )
    def shopping_cart(self, request, id):
        """Текущий пользователь добавляет рецепт в корзину по id"""
        user = request.user
        recipe = self.get_object()
        serializer = ShoppingSerializer(
            data={
                'recipe': recipe.id,
                'user': user.id,
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        recipe.shopping_carts.add(user)
        serializer = ShoppingCartSerializer(recipe)
        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED
        )

    @shopping_cart.mapping.delete
    def delete_from_shopping_cart(self, request, id):
        """Текущий пользователь удаляет рецепт из корзины по id"""
        user = request.user
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('id'))
        if recipe not in user.in_shopping_cart_recipes.all():
            return Response(
                {'This recipe is not in your shopping cart'},
                status=status.HTTP_400_BAD_REQUEST)
        recipe.shopping_carts.remove(user)
        return Response(status=status.HTTP_204_NO_CONTENT)

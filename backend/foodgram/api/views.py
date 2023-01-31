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
from users.models import User

from .filters import RecipeFilter
from .pagination import PageAndLimitPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (ChangePasswordSerializer, FavorSerializer,
                          IngredientSerializer, RecipeSerializer,
                          RecipeWriteSerializer, ShoppingCartSerializer,
                          SubscriptionSerializer, TagSerializer,
                          UserSerializer)


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
    )
    def subscribe(self, request, id):
        """Текущий пользователь подписывается на пользователя с id"""
        user = request.user
        subscribe_to = get_object_or_404(User, id=self.kwargs.get('id'))
        if user == subscribe_to:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if user.subscription.filter(pk=subscribe_to.id).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        user.subscription.add(subscribe_to)
        subscribe_to.is_subscribed = True
        serializer = SubscriptionSerializer(subscribe_to)
        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED
        )

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id):
        """Текущий пользователь удаляет подписку на пользователя с id"""
        user = request.user
        subscribe_to = get_object_or_404(User, id=self.kwargs.get('id'))
        if user.subscription.filter(pk=subscribe_to.id).exists():
            user.subscription.remove(subscribe_to)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)


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
        user.is_subscribed = False
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
        # Для вынесения логики проверки на то, что рецепт уже добавлен в
        # Избранное, пришлось создать отдельную новую модель (была не явная)
        # И написать отдельный сериализатор. Если это необходимо слелать и для
        # методов ниже, то готов сделать. Просто есть сомнения, что именно это
        # было необходимо сделать.
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
        if FavorRecipe.objects.filter(user=user, recipe=recipe).exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        # Как перенести данную логику в сериализатор, если нам здесь
        # нечего сериализовать?
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
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('id'))
        if recipe in user.in_shopping_cart_recipes.all():
            return Response(status=status.HTTP_400_BAD_REQUEST)
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
            return Response(status=status.HTTP_400_BAD_REQUEST)
        recipe.shopping_carts.remove(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShoppingCartViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    permission_classes = (
        IsAuthenticated,
    )
    http_method_names = ['post', 'delete', ]
    pagination_class = None

    def perform_create(self, serializer):
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('recipes_id'))
        user = get_object_or_404(User, id=self.kwargs.get('user_id'))
        if user not in recipe.shopping_carts.all():
            recipe.shopping_carts.add(user)
            return Response(status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('recipes_id'))
        user = get_object_or_404(User, id=self.kwargs.get('user_id'))
        if user in recipe.shopping_carts.all():
            recipe.shopping_carts.remove(user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    permission_classes = (
        IsAuthenticated,
    )
    http_method_names = ['post', 'delete', ]
    pagination_class = None
    lookup_field = "id"

    def perform_create(self, serializer):
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('recipes_id'))
        user = get_object_or_404(User, id=self.kwargs.get('user_id'))
        if user not in recipe.favorites.all():
            recipe.favorites.add(user)
            return Response(status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        recipe = get_object_or_404(Recipe, id=self.kwargs.get('recipes_id'))
        user = get_object_or_404(User, id=self.kwargs.get('user_id'))
        if user in recipe.favorites.all():
            recipe.favorites.remove(user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

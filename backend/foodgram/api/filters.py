import django_filters
from recipes.models import Recipe, Tag


class RecipeFilter(django_filters.FilterSet):

    is_favorited = django_filters.NumberFilter(
        field_name='favorites',
        method='filter_favorited'
    )

    is_in_shopping_cart = django_filters.NumberFilter(
        field_name="shopping_carts",
        method='filter_is_in_shopping_cart'
    )

    author = django_filters.CharFilter(
        field_name="author__id",
        lookup_expr="icontains"
    )

    tags = django_filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        queryset=Tag.objects.all(),
        to_field_name='slug'
    )

    def filter_favorited(self, queryset, name, value):
        if value:
            return queryset.filter(favorites__isnull=False)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if value:
            return queryset.filter(shopping_carts__isnull=False)
        return queryset

    class Meta:
        model = Recipe
        fields = ('author', 'tags')

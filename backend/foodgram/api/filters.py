import django_filters
from recipes.models import Recipe


class RecipeFilter(django_filters.FilterSet):

    is_favorited = django_filters.CharFilter(
        field_name='favorites',
        method='filter_favorited'
    )

    is_in_shopping_cart = django_filters.CharFilter(
        field_name="shopping_carts",
        method='filter_is_in_shopping_cart'
    )

    author = django_filters.CharFilter(
        field_name="author__id",
        lookup_expr="icontains"
    )

    tags = django_filters.AllValuesMultipleFilter(
        field_name='tags__slug',
        method='filter_tags'
    )

    def filter_tags(self, queryset, name, tags):
        return queryset.filter(tags__slug__in=tags, tags__slug__isnull=True)

    def filter_favorited(self, queryset, name, value):
        if int(value):
            return queryset.filter(favorites__isnull=False)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if int(value):
            return queryset.filter(shopping_carts__isnull=False)
        return queryset

    class Meta:
        model = Recipe
        fields = ('favorites', 'shopping_carts', 'author', 'tags')

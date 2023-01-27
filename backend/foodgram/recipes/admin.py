from django.contrib import admin

from .models import Ingredient, IngredientsAmount, Recipe, Tag


class TagAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'color',
        'slug',
    ]
    list_display_links = ('id', 'name',)
    empty_value_display = '-пусто-'


class IngredientAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'measurement_unit',
    ]
    list_display_links = ('id', 'name',)
    empty_value_display = '-пусто-'
    list_filter = (
        'name',
    )


class IngredientsAmountInline(admin.TabularInline):
    model = IngredientsAmount
    extra = 1
    min_num = 1
    verbose_name = "Ингридиенты и их количество"


class RecipeAdmin(admin.ModelAdmin):

    inlines = [IngredientsAmountInline]
    list_display = [
        'id',
        'author',
        'name',
        'favorite_count',
        'get_tags',
    ]
    list_display_links = ('id', 'name',)

    @admin.display(description='Теги')
    def get_tags(self, obj):
        if obj.tags.all():
            return list(obj.tags.all().values_list('name', flat=True))

    def favorite_count(self, obj):
        return obj.favorites.count()
    favorite_count.short_description = 'Число добавлений в избранное'

    empty_value_display = '-пусто-'
    list_filter = (
        'author',
        'name',
        'tags',
    )


admin.site.register(Tag, TagAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Recipe, RecipeAdmin)

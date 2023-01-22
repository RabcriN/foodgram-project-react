from django.contrib import admin

from .models import Ingredient, IngredientsAmount, Recipe, Tag


class TagAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'color',
        'slug',
    ]
    empty_value_display = '-пусто-'


class IngredientAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'measurement_unit',
    ]
    empty_value_display = '-пусто-'
    list_filter = (
        'name',
    )


class IngredientsAmountInline(admin.TabularInline):
    model = IngredientsAmount
    extra = 1


class RecipeAdmin(admin.ModelAdmin):

    inlines = [IngredientsAmountInline]
    list_display = [
        'id',
        'author',
        'name',
        'favorite_count',
    ]

    def favorite_count(self, obj):
        return obj.is_favorited.count()
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

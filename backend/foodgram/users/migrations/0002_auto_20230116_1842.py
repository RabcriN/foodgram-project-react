# Generated by Django 3.2 on 2023-01-16 15:42

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=245, unique=True, verbose_name='Email'),
        ),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(max_length=150, validators=[django.core.validators.RegexValidator('^[\\w.@+-]+\\Z', 'Enter a valid username.')], verbose_name='Юзернейм'),
        ),
    ]
import csv

from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    DATA = {
        Ingredient: "ingredients.csv",
    }

    def add_arguments(self, parser):
        parser.add_argument("--data_directory", type=str)

    def handle(self, *args, **options):
        dirname = options["data_directory"] or '/data'
        for model, filename in self.DATA.items():
            with open(
                f"{dirname}/{filename}",
                newline="",
                encoding="utf-8"
            ) as csvfile:
                reader = csv.reader(csvfile, delimiter=",")
                for row in reader:
                    model.objects.update_or_create(
                        name=row[0],
                        measurement_unit=row[1]
                    )
            print(f"{filename} successfully added to DB")
        print("DB successfully filled")

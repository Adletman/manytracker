from datetime import date
from decimal import Decimal
import factory
from django.contrib.auth import get_user_model
from expenses.models import ExpenseCategory, Expense, Topup

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    full_name = factory.Faker("name")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "testpass1234")
        if create:
            self.save()


class AdminFactory(UserFactory):
    is_admin = True
    is_staff = True
    is_superuser = True


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExpenseCategory

    name = factory.Sequence(lambda n: f"Категория {n}")


class TopupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Topup

    user = factory.SubFactory(UserFactory)
    amount = Decimal("10000.00")
    date = factory.LazyFunction(date.today)
    created_by = factory.SubFactory(AdminFactory)


class ExpenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Expense

    user = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory)
    amount = Decimal("1500.00")
    date = factory.LazyFunction(date.today)

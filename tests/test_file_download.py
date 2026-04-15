from decimal import Decimal
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from tests.factories import UserFactory, AdminFactory, CategoryFactory, TopupFactory
from expenses.models import Expense, ExpenseAttachment


@pytest.fixture
def expense_with_file(db):
    u = UserFactory()
    admin = AdminFactory()
    TopupFactory(user=u, amount=Decimal("10000"), created_by=admin)
    cat = CategoryFactory()
    e = Expense.objects.create(user=u, category=cat, amount=Decimal("500"), date="2026-04-01")
    f = SimpleUploadedFile("chek.pdf", b"PDFDATA", content_type="application/pdf")
    att = ExpenseAttachment.objects.create(
        expense=e, file=f, original_name="chek.pdf",
        mime_type="application/pdf", size=7,
    )
    return u, att


@pytest.mark.django_db
def test_owner_can_download(client, expense_with_file):
    u, att = expense_with_file
    client.force_login(u)
    resp = client.get(f"/attachments/{att.id}/")
    assert resp.status_code == 200
    body = b"".join(resp.streaming_content) if hasattr(resp, "streaming_content") else resp.content
    assert b"PDFDATA" in body


@pytest.mark.django_db
def test_other_user_cannot_download(client, expense_with_file):
    _, att = expense_with_file
    other = UserFactory()
    client.force_login(other)
    resp = client.get(f"/attachments/{att.id}/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_admin_can_download(client, expense_with_file):
    _, att = expense_with_file
    admin = AdminFactory()
    client.force_login(admin)
    resp = client.get(f"/attachments/{att.id}/")
    assert resp.status_code == 200

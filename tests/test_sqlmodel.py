import pytest
from tests.conftest import create_test_db
from lazy_alchemy import get_lazy_class


def test_as_sqlmodel_generates_sqlmodel():
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    User = lazy_db.user.as_sqlmodel()
    assert User.__tablename__ == "user"
    assert "username" in User.model_fields
    assert "age" in User.model_fields


def test_sqlmodel_primary_key():
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    User = lazy_db.user.as_sqlmodel()
    # username is the primary key
    user_fields = User.model_fields
    assert "username" in user_fields


def test_sqlmodel_optional_fields():
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    User = lazy_db.user.as_sqlmodel()
    # age should not be required
    user_fields = User.model_fields
    assert user_fields["age"].is_required() is False
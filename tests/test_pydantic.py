import pytest
from tests.conftest import create_test_db
from lazy_alchemy import get_lazy_class
from pydantic import BaseModel


def test_as_pydantic_generates_model():
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    UserSchema = lazy_db.user.as_pydantic()
    assert issubclass(UserSchema, BaseModel)
    assert "username" in UserSchema.model_fields
    assert "age" in UserSchema.model_fields


def test_as_pydantic_partial_optional():
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    UserPatch = lazy_db.user.as_pydantic_partial()
    assert UserPatch.model_fields["username"].is_required() is False


def test_pydantic_validation():
    engine = create_test_db()
    lazy_db = get_lazy_class(engine)
    UserSchema = lazy_db.user.as_pydantic()
    user = UserSchema(username="alice", age=30)
    assert user.username == "alice"
    assert user.age == 30
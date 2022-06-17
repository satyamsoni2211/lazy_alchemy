import os
import pytest
from glob import glob
from sqlalchemy import Column
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoSuchTableError
from unittest import TestCase
from .seed_db import create_table
from lazy_alchemy import get_lazy_class, CustomTable


class TestLazyOrmSuite(TestCase):
    def setUp(self) -> None:
        self.engine = create_table()
        self.session = Session(self.engine)
        self.lazy_class = get_lazy_class(self.engine)

    def test_lazy_db_connection(self):
        table = self.lazy_class.user
        self.assertIsInstance(table, CustomTable)
        self.assertIsInstance(table.username, Column)
        self.assertIsInstance(table.age, Column)
        self.assertEqual(table.name, "user")
        self.assertEqual(len(table.constraints), 1)
        self.assertTrue(
            any(i for i in table.indexes if i.name == "idx_user_username"))

    def test_insert_operation_on_dynamic_class(self):
        user: CustomTable = self.lazy_class.user
        self.assertTrue(user)
        insert_statement = user.insert().values(username="fake_user", age=21)
        self.session.execute(insert_statement)
        self.session.commit()
        obj = self.session.query(user).first()
        self.assertEqual(obj.username, "fake_user")
        self.assertEqual(obj.age, 21)

    def test_invalid_table_and_column(self):
        with pytest.raises(NoSuchTableError):
            self.lazy_class.foo_bar
        with pytest.raises(AttributeError):
            self.lazy_class.user.abc

    def test_overriding_table(self):
        _ = self.lazy_class.user
        self.lazy_class.user = CustomTable("userabc", self.lazy_class.metadata)
        self.assertNotEqual(_, self.lazy_class.user)
        self.assertEqual(self.lazy_class.user.name, "userabc")

    def tearDown(self) -> None:
        self.session.close()
        print(f"cleaning files {glob('*.db')}")
        os.unlink("test.db")

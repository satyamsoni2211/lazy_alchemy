import os
from glob import glob
from sqlalchemy import Column
from sqlalchemy.orm import Session
from unittest import TestCase
from .seed_db import create_table
from lazy_alchemy import get_lazy_class, CustomTable


class TestLazyOrmSuite(TestCase):
    def setUp(self) -> None:
        self.engine = create_table()
        self.session = Session(self.engine)
        self.lazy_class = get_lazy_class(self.engine)

    def test_lazy_db_connection(self):
        self.assertIsInstance(self.lazy_class.user, CustomTable)
        self.assertIsInstance(self.lazy_class.user.username, Column)
        self.assertIsInstance(self.lazy_class.user.age, Column)

    def test_insert_operation_on_dynamic_class(self):
        user: CustomTable = self.lazy_class.user
        insert_statement = user.insert().values(username="fake_user", age=21)
        self.session.execute(insert_statement)
        self.session.commit()
        obj = self.session.query(user).first()
        self.assertEqual(obj.username, "fake_user")
        self.assertEqual(obj.age, 21)

    def tearDown(self) -> None:
        self.session.close()
        print(f"cleaning files {glob('*.db')}")
        os.unlink("test.db")

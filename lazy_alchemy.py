from sqlalchemy import Table, MetaData
from sqlalchemy.engine import Engine


class CustomTable(Table):
    def __getattr__(self, attr):
        return getattr(self.c, attr)


class LazyDBProp(object):
    """This descriptor returns sqlalchemy
    Table class which can be used to query
    table from the schema
    """

    def __init__(self) -> None:
        self._table = None
        self._name = None

    def __set_name__(self, owner, name):
        self._name = name

    def __set__(self, instance, value):
        pass

    def __get__(self, instance, owner):
        if self._table is None:
            self._table = CustomTable(
                self._name, instance.metadata, autoload=True)
        return self._table


def get_lazy_class(engine: Engine) -> object:
    """
    Function to create Lazy class for pulling table object
    using SQLalchemy metadata
    """

    def __init__(self, engine: Engine):
        self.metadata = MetaData(engine)
        self.engine = engine

    def __getattr__(self, attr):
        if attr not in self.__dict__:
            obj = self.__patch(attr)
        return obj.__get__(self, type(self))

    def __patch(self, attribute):
        obj = LazyDBProp()
        obj.__set_name__(self, attribute)
        setattr(type(self), attribute, obj)
        return obj

    # naming classes uniquely for different schema's
    # to avoid cross referencing
    LazyClass = type(f"LazyClass_{engine.url.database}", (), {})
    LazyClass.__init__ = __init__
    LazyClass.__getattr__ = __getattr__
    LazyClass.__patch = __patch
    return LazyClass(engine)

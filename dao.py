import ZODB
import ZODB.FileStorage
import transaction
from persistent import Persistent


class Photograph(Persistent):
    filepath = None
    filetype = None
    version = None

    def __init__(self, filepath, filetype, version):
        self.filepath = filepath
        self.filetype = filetype
        self.version = version

    def __str__(self):
        return f"Photograph(filepath=[{self.filepath}], filetype=[{self.filetype}], version=[{self.version}])"


class ZODBDAO(object):
    _storage = None
    _db = None
    _connection = None
    _root = None

    def __init__(self, filepath):
        self._storage = ZODB.FileStorage.FileStorage(filepath)
        self._db = ZODB.DB(storage)
        self._connection = db.open()
        self._root = connection.root()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def close(self):
        self._root = None
        self._connection.close()
        self._db.close()
        self._storage.close()

    @property
    def root(self):
        return self._root



if __name__ == '__main__':
    PHOTOGRAPHS_KEY = 'photographs'

    def list_photographs(root):
        pass

    def add_photograph(root, photograph):
        pass

    with ZODBDAO('photolibrary.fs') as dao:
        root = dao.root
        if not root.has_key(PHOTOGRAPHS_KEY):
            root[PHOTOGRAPHS_KEY] = {}
        photographs = root[PHOTOGRAPHS_KEY]

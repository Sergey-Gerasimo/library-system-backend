from services.crud import IStorageRUD, IBookFilesCRUD


class StorageService:
    def __init__(self, storage_crud: IStorageRUD, book_files_crud: IBookFilesCRUD):
        self._storage_crud = storage_crud
        self._book_files_crud = book_files_crud

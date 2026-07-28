import os
import uuid
import logging
from fastapi import UploadFile
from app.config import settings

logger = logging.getLogger("storage")

class StorageService:
    def __init__(self):
        self.base_dir = "./storage_data"
        os.makedirs(self.base_dir, exist_ok=True)

    async def save_resume(self, user_id: int, file: UploadFile) -> str:
        user_folder = os.path.join(self.base_dir, str(user_id))
        os.makedirs(user_folder, exist_ok=True)

        filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(user_folder, filename)

        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        return file_path

    def get_resume_bytes(self, file_path: str) -> bytes:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                return f.read()
        raise FileNotFoundError(f"File not found: {file_path}")

    def delete_resume_file(self, file_path: str) -> bool:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            logger.warning(f"Could not delete resume file {file_path}: {e}")
        return False

storage_service = StorageService()

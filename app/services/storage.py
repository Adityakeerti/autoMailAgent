import os
import uuid
from fastapi import UploadFile
from app.config import settings

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

storage_service = StorageService()

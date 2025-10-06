from pathlib import Path
from fastapi import UploadFile
from typing import List
import zipfile


async def save_upload_to_disk(file: UploadFile, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    contents = await file.read()
    dest.write_bytes(contents)


def extract_zip(zip_path: Path, extract_to: Path) -> None:
    extract_to.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_to)


async def save_folder_upload(files: List[UploadFile], root: Path) -> None:
    """Save multiple uploaded files preserving relative paths from filename.
    The browser can send directory uploads by setting filename to webkitRelativePath.
    """
    root.mkdir(parents=True, exist_ok=True)
    for f in files:
        # Use UploadFile.filename which contains relative path if provided
        rel = f.filename or ""
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        contents = await f.read()
        dest.write_bytes(contents)
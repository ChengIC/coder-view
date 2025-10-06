from pathlib import Path
from fastapi import UploadFile
from typing import List, Dict
import tempfile
import os


async def process_folder_upload(files: List[UploadFile]) -> Dict[str, str]:
    """Process uploaded files directly in memory and return file contents."""
    file_contents = {}
    
    for file in files:
        try:
            # Get relative path from filename (browser sets this for folder uploads)
            rel_path = file.filename or file.filename
            if not rel_path:
                continue
                
            # Read file content directly
            content = await file.read()
            
            # Store as string (decode with error handling)
            try:
                file_contents[rel_path] = content.decode('utf-8')
            except UnicodeDecodeError:
                # Skip binary files or files that can't be decoded
                continue
                
        except Exception as e:
            # Skip files that can't be processed
            continue
    
    return file_contents


def create_temp_files(file_contents: Dict[str, str]) -> str:
    """Create temporary files for analysis and return the temp directory path."""
    temp_dir = tempfile.mkdtemp()
    
    for rel_path, content in file_contents.items():
        file_path = Path(temp_dir) / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            file_path.write_text(content, encoding='utf-8')
        except Exception:
            # Skip files that can't be written
            continue
    
    return temp_dir
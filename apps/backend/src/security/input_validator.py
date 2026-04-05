"""Input validation and sanitization."""
import os
from typing import Tuple

import magic

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class InputValidator:
    """Validates file uploads and inputs."""
    
    # MIME type mapping
    ALLOWED_MIME_TYPES = {
        ".pdf": ["application/pdf"],
        ".docx": [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",  # DOCX is a zip file
        ],
        ".xlsx": [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/zip",
        ],
        ".csv": ["text/csv", "text/plain"],
        ".txt": ["text/plain"],
        ".pptx": [
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/zip",
        ],
        ".md": ["text/plain", "text/markdown"],
    }
    
    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate uploaded file.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file exists
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > settings.max_upload_size_bytes:
            return False, f"File too large: {file_size} bytes (max: {settings.max_upload_size_bytes})"
        
        if file_size == 0:
            return False, "File is empty"
        
        # Check extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext not in settings.allowed_extensions:
            return False, f"File extension not allowed: {ext}"
        
        # Check MIME type (magic bytes)
        try:
            mime = magic.Magic(mime=True)
            detected_mime = mime.from_file(file_path)
            
            allowed_mimes = self.ALLOWED_MIME_TYPES.get(ext, [])
            if detected_mime not in allowed_mimes:
                logger.warning(
                    "mime_type_mismatch",
                    extension=ext,
                    detected=detected_mime,
                    allowed=allowed_mimes,
                )
                # Don't block, but log warning
        except Exception as e:
            logger.warning("mime_type_check_failed", error=str(e))
        
        # Check for path traversal
        if ".." in file_path or file_path.startswith("/"):
            return False, "Invalid file path"
        
        return True, ""
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        dangerous_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*", "\x00"]
        for char in dangerous_chars:
            filename = filename.replace(char, "_")
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250] + ext
        
        return filename

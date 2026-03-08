"""
Storage service for project code files — Nhost Storage backend.

All operations delegate to storage_nhost.py.
Files are stored in the 'project-files' bucket at:
    {project_id}/{file_path}   e.g.  abc-123/src/App.tsx
"""
from storage_nhost import (
    ensure_bucket_exists,
    upload_file_sync,
    upload_files_sync,
    download_file_sync,
    download_project_files_sync,
    delete_file_sync,
    delete_project_files_sync,
    delete_all_project_files_sync,
    upload_files,
    download_project_files,
)

__all__ = [
    "ensure_bucket_exists",
    "upload_file_sync",
    "upload_files_sync",
    "download_file_sync",
    "download_project_files_sync",
    "delete_file_sync",
    "delete_project_files_sync",
    "delete_all_project_files_sync",
    "upload_files",
    "download_project_files",
]


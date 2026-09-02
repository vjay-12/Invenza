import uuid
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import StreamingResponse
from app.services.storage import StorageService

router = APIRouter()

@router.get("/health")
def storage_health():
    """Verify MinIO connection and bucket accessibility."""
    try:
        StorageService.get_client()
        files = StorageService.list_files()
        return {
            "status": "connected",
            "storage_provider": "MinIO S3 Object Storage",
            "bucket": "invenza-documents",
            "stored_objects_count": len(files),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MinIO storage unreachable: {str(e)}",
        )

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form("attachment"),
    reference_id: Optional[str] = Form(""),
):
    """
    Upload a document, invoice, receipt, or product image to MinIO S3 object storage.
    """
    try:
        contents = await file.read()
        safe_filename = file.filename.replace(" ", "_")
        object_name = f"{document_type}/{str(uuid.uuid4())[:8]}_{safe_filename}"
        
        result = StorageService.upload_file(
            file_bytes=contents,
            object_name=object_name,
            content_type=file.content_type or "application/octet-stream",
            metadata={
                "original_filename": file.filename,
                "document_type": document_type or "attachment",
                "reference_id": reference_id or "",
            }
        )
        return {
            "status": "uploaded",
            "filename": file.filename,
            "document_type": document_type,
            "reference_id": reference_id,
            "object_name": result["object_name"],
            "size_bytes": result["size"],
            "url": result["url"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to MinIO: {str(e)}"
        )

@router.get("/files/{object_name:path}")
def get_stored_file(object_name: str):
    """
    Stream a stored file directly from MinIO S3 storage.
    """
    try:
        obj = StorageService.get_file(object_name)
        return StreamingResponse(
            obj.stream(32 * 1024),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"inline; filename={object_name.split('/')[-1]}"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found in MinIO: {str(e)}"
        )

@router.get("/list")
def list_documents():
    """
    List all documents and attachments stored in MinIO.
    """
    return StorageService.list_files()

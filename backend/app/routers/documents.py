from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.utils.dependencies import get_current_active_user
from app.services.document_analysis_service import DocumentAnalysisService
from app.core.logging import logger
from app.models.user import User

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze a document (image or PDF) and extract financial data.

    Returns a draft with extracted information. NEVER executes payments.
    The user must explicitly confirm any action suggested by the analysis.

    Accepted types: PNG, JPG, WebP, PDF (max 5MB).
    """
    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine file type"
        )

    content_type = file.content_type.lower()
    allowed_types = {
        "image/png", "image/jpeg", "image/jpg", "image/webp",
        "application/pdf",
    }

    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {content_type}. Allowed: PNG, JPG, WebP, PDF"
        )

    content = await file.read()

    if len(content) > DocumentAnalysisService.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large (max 5MB)"
        )

    logger.info(f"Document analysis requested by user {current_user.id}, type={content_type}, size={len(content)}")

    service = DocumentAnalysisService()
    result = await service.analyze_content(content, content_type)

    logger.info(
        f"Document analysis result for user {current_user.id}: "
        f"type={result.get('document_type')}, confidence={result.get('confidence')}, "
        f"action={result.get('suggested_action')}"
    )

    return result

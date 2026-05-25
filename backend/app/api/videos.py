from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime
from typing import List

from app.database import get_db
from app.models.video import Video, VideoStatus
from app.models.user import User
from app.api.auth import get_current_user
from app.schemas.video import (
    VideoUploadResponse,
    VideoStatusResponse,
    VideoDetailResponse,
    VideoListResponse,
)
from app.services.video_processor import video_processor

router = APIRouter()


async def update_video_progress(db: AsyncSession, video_id: str, status: str, progress: int):
    """Background task to update video processing progress"""
    result = await db.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if video:
        video.status = status
        video.progress = progress
        if status == VideoStatus.COMPLETED.value:
            video.completed_at = datetime.utcnow()
        await db.commit()


async def process_video_background(video_id: str, video_path: str, db_url: str):
    """Background task to process video"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        try:
            async def progress_callback(status: str, progress: int):
                result = await db.execute(select(Video).where(Video.id == video_id))
                video = result.scalar_one_or_none()
                if video:
                    video.status = status
                    video.progress = progress
                    await db.commit()

            result = await video_processor.process_video_complete(
                video_id, video_path, progress_callback
            )

            # Update final result
            query_result = await db.execute(select(Video).where(Video.id == video_id))
            video = query_result.scalar_one_or_none()
            if video:
                video.duration = result.get("duration", 0)
                video.audio_path = result.get("audio_path")
                video.transcript = result.get("transcript")
                video.frames_dir = result.get("frames_dir")
                video.frame_count = result.get("frame_count", 0)
                video.analysis_result = result.get("analysis_result")
                video.generated_blocks = result.get("generated_blocks")

                if result.get("error"):
                    video.status = VideoStatus.FAILED.value
                    video.error_message = result["error"]
                else:
                    video.status = VideoStatus.COMPLETED.value
                    video.progress = 100
                    video.completed_at = datetime.utcnow()

                await db.commit()

        except Exception as e:
            query_result = await db.execute(select(Video).where(Video.id == video_id))
            video = query_result.scalar_one_or_none()
            if video:
                video.status = VideoStatus.FAILED.value
                video.error_message = str(e)
                await db.commit()


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a video for processing"""
    # Validate file type
    allowed_types = ["video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # Read and save file
    content = await file.read()
    filename, file_path, file_size = await video_processor.save_uploaded_video(
        content, file.filename
    )

    # Create video record
    video = Video(
        owner_id=current_user.id,
        filename=filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        status=VideoStatus.PROCESSING.value,
        progress=0,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    # Start background processing
    from app.config import settings
    background_tasks.add_task(
        process_video_background,
        video.id,
        file_path,
        settings.DATABASE_URL,
    )

    return VideoUploadResponse(
        id=video.id,
        filename=video.original_filename,
        status=video.status,
        message="영상 업로드 완료. 처리를 시작합니다.",
    )


@router.get("", response_model=VideoListResponse)
async def list_videos(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all videos for current user"""
    result = await db.execute(
        select(Video)
        .where(Video.owner_id == current_user.id)
        .order_by(desc(Video.created_at))
    )
    videos = result.scalars().all()

    return VideoListResponse(
        videos=[VideoStatusResponse.model_validate(v) for v in videos],
        total=len(videos),
    )


@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get video details including analysis results"""
    result = await db.execute(
        select(Video).where(
            Video.id == video_id,
            Video.owner_id == current_user.id,
        )
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return VideoDetailResponse.model_validate(video)


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get video processing status"""
    result = await db.execute(
        select(Video).where(
            Video.id == video_id,
            Video.owner_id == current_user.id,
        )
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    return VideoStatusResponse.model_validate(video)


@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a video"""
    result = await db.execute(
        select(Video).where(
            Video.id == video_id,
            Video.owner_id == current_user.id,
        )
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # Delete files
    import os
    from pathlib import Path

    if video.file_path and os.path.exists(video.file_path):
        os.remove(video.file_path)
    if video.audio_path and os.path.exists(video.audio_path):
        os.remove(video.audio_path)
    if video.frames_dir and os.path.exists(video.frames_dir):
        import shutil
        shutil.rmtree(video.frames_dir)

    await db.delete(video)
    await db.commit()

    return {"message": "Video deleted successfully"}


@router.post("/{video_id}/apply-blocks")
async def apply_generated_blocks(
    video_id: str,
    workspace_name: str = "영상 기반 자동화",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apply generated blocks from video analysis to a new workspace"""
    result = await db.execute(
        select(Video).where(
            Video.id == video_id,
            Video.owner_id == current_user.id,
        )
    )
    video = result.scalar_one_or_none()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not video.generated_blocks:
        raise HTTPException(status_code=400, detail="No generated blocks available")

    # Create new workspace with blocks
    from app.models.workspace import Workspace

    workspace = Workspace(
        owner_id=current_user.id,
        name=workspace_name,
        description=f"영상 분석으로 생성됨: {video.original_filename}",
        blocks_data=video.generated_blocks,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)

    return {
        "message": "Workspace created successfully",
        "workspace_id": workspace.id,
        "block_count": len(video.generated_blocks),
    }

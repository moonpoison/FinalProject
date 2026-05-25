import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class VideoStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    EXTRACTING_AUDIO = "extracting_audio"
    EXTRACTING_FRAMES = "extracting_frames"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)

    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=True)  # seconds

    status = Column(String(50), default=VideoStatus.UPLOADING.value)
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text, nullable=True)

    # Processing results
    audio_path = Column(String(500), nullable=True)
    transcript = Column(Text, nullable=True)
    frame_count = Column(Integer, default=0)
    frames_dir = Column(String(500), nullable=True)

    # Analysis results
    analysis_result = Column(JSON, nullable=True)
    generated_blocks = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="videos")

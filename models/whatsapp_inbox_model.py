from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class SenderType(str, Enum):
    CUSTOMER = "customer"
    AI_AGENT = "ai_agent"
    HUMAN_AGENT = "human_agent"


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    LOCATION = "location"
    TEMPLATE = "template"


class MessageStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class ConversationStatus(str, Enum):
    OPEN = "open"
    PENDING_HUMAN = "pending_human"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IngestWhatsappMessage(BaseModel):
    wamid: str = Field(..., min_length=1)
    customer_phone: str = Field(..., min_length=5)
    customer_name: Optional[str] = None

    direction: MessageDirection
    sender_type: SenderType
    message_type: MessageType = MessageType.TEXT

    text_body: Optional[str] = None
    media_url: Optional[str] = None

    status: MessageStatus = MessageStatus.PENDING
    message_timestamp: Optional[datetime] = None

    reply_to_wamid: Optional[str] = None


class SendWhatsappMessage(BaseModel):

    text_body: str = Field(..., min_length=1, max_length=4096)
    message_type: MessageType = MessageType.TEXT
    reply_to_wamid: Optional[str] = None


class UpdateConversationStatus(BaseModel):
    status: ConversationStatus


class UpdateMessageStatus(BaseModel):
    wamid: str = Field(..., min_length=1)
    status: MessageStatus
    status_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None


class WhatsappMessageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    conversation_id: str
    wamid: Optional[str] = None

    direction: MessageDirection
    sender_type: SenderType
    message_type: MessageType

    text_body: Optional[str] = None
    media_url: Optional[str] = None

    status: MessageStatus

    created_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None

    error_message: Optional[str] = None


class WhatsappConversationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    customer_phone: str
    customer_name: Optional[str] = None

    status: ConversationStatus = ConversationStatus.OPEN

    unread_count: int = 0
    last_message_text: Optional[str] = None
    last_message_at: Optional[datetime] = None

    assigned_to: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WhatsappConversationDetailResponse(WhatsappConversationResponse):
    messages: List[WhatsappMessageResponse] = []


class PaginatedWhatsappConversationResponse(BaseModel):
    total_results: int
    page: int
    limit: int
    total_pages: int
    data: List[WhatsappConversationResponse]


class PaginatedWhatsappMessageResponse(BaseModel):
    total_results: int
    page: int
    limit: int
    total_pages: int
    data: List[WhatsappMessageResponse]
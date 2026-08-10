from typing import Optional
from fastapi import (APIRouter,Depends,Query,status)
from auth.dependencies import get_current_user
from controller.whatsapp_inbox_controller import (WhatsappInboxController)
from db.database import get_db
from models.base_model import StandardResponse
from models.whatsapp_inbox_model import (
    ConversationStatus,
    IngestWhatsappMessage,
    PaginatedWhatsappConversationResponse,
    PaginatedWhatsappMessageResponse,
    SendWhatsappMessage,
    UpdateConversationStatus,
    UpdateMessageStatus,
    WhatsappConversationDetailResponse,
    WhatsappConversationResponse,
    WhatsappMessageResponse,
)


router = APIRouter(prefix="/whatsapp-inbox",tags=["WhatsApp Inbox"],)

@router.post(
    "/ingest",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse[WhatsappMessageResponse],
)
async def ingest_whatsapp_message(
    payload: IngestWhatsappMessage,
    db=Depends(get_db),
):
    result = await WhatsappInboxController.ingest_message(
        payload=payload,
        db=db,
    )

    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="WhatsApp message stored successfully",
        result_data=result,
    )

# send human whatsapp message
@router.post(
    "/conversations/{conversation_id}/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=StandardResponse[WhatsappMessageResponse],
)
async def send_human_whatsapp_message(
    conversation_id: str,
    payload: SendWhatsappMessage,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await WhatsappInboxController.send_human_message(
        conversation_id=conversation_id,
        payload=payload,
        db=db,
    )

    return StandardResponse(
        status_code=status.HTTP_201_CREATED,
        message="Human message queued successfully",
        result_data=result,
    )

# left side conversations
@router.get(
    "/conversations",
    response_model=StandardResponse[
        PaginatedWhatsappConversationResponse
    ],
)
async def get_whatsapp_conversations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=1000),
    conversation_status: Optional[ConversationStatus] = Query(
        default=None,
        alias="status",
    ),
    search: Optional[str] = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await WhatsappInboxController.get_conversations(
        page=page,
        limit=limit,
        db=db,
        status_filter=conversation_status,
        search=search,
    )

    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="WhatsApp conversations fetched successfully",
        result_data=result,
    )

# one user conversation
@router.get(
    "/conversations/{conversation_id}",
    response_model=StandardResponse[
        WhatsappConversationDetailResponse
    ],
)
async def get_whatsapp_conversation(
    conversation_id: str,
    db=Depends(get_db),
    # _: dict = Depends(get_current_user),
):
    result = await WhatsappInboxController.get_conversation_by_id(
        conversation_id=conversation_id,
        db=db,
    )

    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="WhatsApp conversation fetched successfully",
        result_data=result,
    )

# if want to load messages separately with pagination
@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=StandardResponse[
        PaginatedWhatsappMessageResponse
    ],
)
async def get_whatsapp_messages(
    conversation_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await WhatsappInboxController.get_messages(
        conversation_id=conversation_id,
        page=page,
        limit=limit,
        db=db,
    )

    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="WhatsApp messages fetched successfully",
        result_data=result,
    )

# whatsapp message status update
@router.patch(
    "/messages/status",
    response_model=StandardResponse[WhatsappMessageResponse],
)
async def update_whatsapp_message_status(
    payload: UpdateMessageStatus,
    db=Depends(get_db),
):
    result = await WhatsappInboxController.update_message_status(
        payload=payload,
        db=db,
    )

    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="WhatsApp message status updated successfully",
        result_data=result,
    )


# update conversation status
@router.patch(
    "/conversations/{conversation_id}/status",
    response_model=StandardResponse[
        WhatsappConversationResponse
    ],
)
async def update_whatsapp_conversation_status(
    conversation_id: str,
    payload: UpdateConversationStatus,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await WhatsappInboxController.update_conversation_status(
        conversation_id=conversation_id,
        payload=payload,
        db=db,
    )

    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Conversation status updated successfully",
        result_data=result,
    )


@router.patch(
    "/conversations/{conversation_id}/read",
    response_model=StandardResponse[
        WhatsappConversationResponse
    ],
)
async def mark_whatsapp_conversation_read(
    conversation_id: str,
    db=Depends(get_db),
    _: dict = Depends(get_current_user),
):
    result = await WhatsappInboxController.mark_conversation_read(
        conversation_id=conversation_id,
        db=db,
    )

    return StandardResponse(
        status_code=status.HTTP_200_OK,
        message="Conversation marked as read",
        result_data=result,
    )
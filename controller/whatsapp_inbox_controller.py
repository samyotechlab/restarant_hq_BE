import math
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import HTTPException
import httpx

from config.settings import settings
from models.whatsapp_inbox_model import (
    ConversationStatus,
    IngestWhatsappMessage,
    MessageDirection,
    MessageStatus,
    PaginatedWhatsappConversationResponse,
    PaginatedWhatsappMessageResponse,
    SendWhatsappMessage,
    SenderType,
    UpdateConversationStatus,
    UpdateMessageStatus,
    WhatsappConversationDetailResponse,
    WhatsappConversationResponse,
    WhatsappMessageResponse,
)


class WhatsappInboxController:
    CONVERSATIONS_COLLECTION = "whatsapp_conversations"
    MESSAGES_COLLECTION = "whatsapp_messages"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _get_object_id(value: str) -> ObjectId:
        if not ObjectId.is_valid(value):
            raise HTTPException(
                status_code=400,
                detail="Invalid conversation id",
            )

        return ObjectId(value)

    @staticmethod
    def _message_to_response(doc: dict) -> WhatsappMessageResponse:
        doc = dict(doc)

        document_id = doc.pop("_id", None)
        conversation_id = doc.get("conversation_id")

        doc["id"] = str(document_id)
        doc["conversation_id"] = str(conversation_id)

        return WhatsappMessageResponse(**doc)

    @staticmethod
    def _conversation_to_response(
        doc: dict,
    ) -> WhatsappConversationResponse:
        doc = dict(doc)

        document_id = doc.pop("_id", None)
        doc["id"] = str(document_id)

        return WhatsappConversationResponse(**doc)

    @staticmethod
    async def create_indexes(db):
        await db[
            WhatsappInboxController.MESSAGES_COLLECTION
        ].create_index(
            "wamid",
            unique=True,
            sparse=True,
        )

        await db[
            WhatsappInboxController.CONVERSATIONS_COLLECTION
        ].create_index(
            "customer_phone",
            unique=True,
        )

        await db[
            WhatsappInboxController.MESSAGES_COLLECTION
        ].create_index(
            [
                ("conversation_id", 1),
                ("created_at", 1),
            ]
        )

        await db[
            WhatsappInboxController.CONVERSATIONS_COLLECTION
        ].create_index(
            [
                ("last_message_at", -1),
            ]
        )

        await db[
            WhatsappInboxController.CONVERSATIONS_COLLECTION
        ].create_index(
            [
                ("status", 1),
                ("last_message_at", -1),
            ]
        )

    @staticmethod
    async def _get_or_create_conversation(
        payload: IngestWhatsappMessage,
        db,
    ) -> dict:
        conversations = db[
            WhatsappInboxController.CONVERSATIONS_COLLECTION
        ]

        conversation = await conversations.find_one(
            {
                "customer_phone": payload.customer_phone,
            }
        )

        if conversation:
            return conversation

        now = WhatsappInboxController._now()
        message_timestamp = payload.message_timestamp or now

        conversation_doc = {
            "country_code": payload.country_code,
            "customer_phone": payload.customer_phone,
            "customer_name": payload.customer_name,
            "status": ConversationStatus.OPEN.value,
            "unread_count": (
                1
                if payload.direction == MessageDirection.INBOUND
                else 0
            ),
            "last_message_text": payload.text_body,
            "last_message_at": message_timestamp,
            "assigned_to": None,
            "created_at": now,
            "updated_at": now,
        }

        result = await conversations.insert_one(conversation_doc)

        return await conversations.find_one(
            {
                "_id": result.inserted_id,
            }
        )

    @staticmethod
    async def ingest_message(
        payload: IngestWhatsappMessage,
        db,
    ) -> WhatsappMessageResponse:
        messages = db[
            WhatsappInboxController.MESSAGES_COLLECTION
        ]

        conversations = db[
            WhatsappInboxController.CONVERSATIONS_COLLECTION
        ]

        now = WhatsappInboxController._now()
        message_timestamp = payload.message_timestamp or now

        existing_message = await messages.find_one(
            {
                "wamid": payload.wamid,
            }
        )

        if existing_message:
            return WhatsappInboxController._message_to_response(
                existing_message
            )

        conversation = await WhatsappInboxController._get_or_create_conversation(
            payload=payload,
            db=db,
        )

        conversation_id = conversation["_id"]

        message_doc = {
            "conversation_id": conversation_id,
            "wamid": payload.wamid,
            "direction": payload.direction.value,
            "sender_type": payload.sender_type.value,
            "message_type": payload.message_type.value,
            "text_body": payload.text_body,
            "media_url": payload.media_url,
            "status": payload.status.value,
            "created_at": now,
            "sent_at": None,
            "delivered_at": None,
            "read_at": None,
            "failed_at": None,
            "error_message": None,
        }

        if payload.status in [
            MessageStatus.SENT,
            MessageStatus.DELIVERED,
            MessageStatus.READ,
        ]:
            message_doc["sent_at"] = message_timestamp

        if payload.status in [
            MessageStatus.DELIVERED,
            MessageStatus.READ,
        ]:
            message_doc["delivered_at"] = message_timestamp

        if payload.status == MessageStatus.READ:
            message_doc["read_at"] = message_timestamp

        try:
            result = await messages.insert_one(message_doc)
        except Exception as error:
            if "duplicate key" in str(error).lower():
                duplicate_message = await messages.find_one(
                    {
                        "wamid": payload.wamid,
                    }
                )

                if duplicate_message:
                    return WhatsappInboxController._message_to_response(
                        duplicate_message
                    )

            raise error

        conversation_update = {
            "last_message_text": payload.text_body,
            "last_message_at": message_timestamp,
            "updated_at": now,
        }

        if payload.customer_name:
            conversation_update["customer_name"] = payload.customer_name

        if payload.direction == MessageDirection.INBOUND:
            await conversations.update_one(
                {
                    "_id": conversation_id,
                },
                {
                    "$set": conversation_update,
                    "$inc": {
                        "unread_count": 1,
                    },
                },
            )
        else:
            await conversations.update_one(
                {
                    "_id": conversation_id,
                },
                {
                    "$set": conversation_update,
                },
            )

        saved_message = await messages.find_one(
            {
                "_id": result.inserted_id,
            }
        )

        return WhatsappInboxController._message_to_response(saved_message)

    @staticmethod
    async def get_conversations(
        page: int,
        limit: int,
        db,
        status_filter: Optional[ConversationStatus] = None,
        search: Optional[str] = None,
    ) -> PaginatedWhatsappConversationResponse:
        conversations = db[
            WhatsappInboxController.CONVERSATIONS_COLLECTION
        ]

        query = {}

        if status_filter:
            query["status"] = status_filter.value

        if search:
            query["$or"] = [
                {
                    "customer_name": {
                        "$regex": search,
                        "$options": "i",
                    }
                },
                {
                    "customer_phone": {
                        "$regex": search,
                        "$options": "i",
                    }
                },
            ]

        total_results = await conversations.count_documents(query)

        skip = (page - 1) * limit

        docs = (await conversations.find(query).sort("last_message_at", -1).skip(skip).limit(limit).to_list(length=None))

        data = [
            WhatsappInboxController._conversation_to_response(doc)
            for doc in docs
        ]

        return PaginatedWhatsappConversationResponse(
            total_results=total_results,
            page=page,
            limit=limit,
            total_pages=(
                math.ceil(total_results / limit)
                if total_results
                else 0
            ),
            data=data,
        )

    @staticmethod
    async def get_conversation_by_id(
        conversation_id: str,
        db,
    ) -> WhatsappConversationDetailResponse:
        conversations = db[WhatsappInboxController.CONVERSATIONS_COLLECTION]

        messages = db[WhatsappInboxController.MESSAGES_COLLECTION]

        conversation = await conversations.find_one(
            {
                "_id": ObjectId(conversation_id),
            }
        )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        message_docs = (
            await messages.find(
                {
                    "conversation_id": ObjectId(conversation_id),
                }
            )
            .sort("created_at", 1)
            .to_list(length=None)
        )

        conversation_response = (
            WhatsappInboxController._conversation_to_response(
                conversation
            )
        )

        return WhatsappConversationDetailResponse(
            **conversation_response.model_dump(),
            messages=[
                WhatsappInboxController._message_to_response(
                    message
                )
                for message in message_docs
            ],
        )

    @staticmethod
    async def get_messages(
        conversation_id: str,
        page: int,
        limit: int,
        db,
    ) -> PaginatedWhatsappMessageResponse:
        conversations = db[WhatsappInboxController.CONVERSATIONS_COLLECTION]

        messages = db[WhatsappInboxController.MESSAGES_COLLECTION]

        object_id = WhatsappInboxController._get_object_id(conversation_id)

        conversation = await conversations.find_one(
            {
                "_id": object_id,
            }
        )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        query = {"conversation_id": object_id}

        total_results = await messages.count_documents(query)

        skip = (page - 1) * limit

        docs = (await messages.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(length=None))

        docs.reverse()

        return PaginatedWhatsappMessageResponse(
            total_results=total_results,
            page=page,
            limit=limit,
            total_pages=(
                math.ceil(total_results / limit)
                if total_results
                else 0
            ),
            data=[
                WhatsappInboxController._message_to_response(doc)
                for doc in docs
            ],
        )

    @staticmethod
    async def send_human_message(conversation_id: str,payload: SendWhatsappMessage,db) -> WhatsappMessageResponse:
        conversations = db[WhatsappInboxController.CONVERSATIONS_COLLECTION]

        messages = db[WhatsappInboxController.MESSAGES_COLLECTION]

        object_id = WhatsappInboxController._get_object_id(conversation_id)

        conversation = await conversations.find_one(
            {
                "_id": object_id,
            }
        )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        now = WhatsappInboxController._now()

        message_doc = {
            "conversation_id": object_id,
            "wamid": None,
            "direction": MessageDirection.OUTBOUND.value,
            "sender_type": SenderType.HUMAN_AGENT.value,
            "message_type": payload.message_type.value,
            "text_body": payload.text_body,
            "media_url": None,
            "status": MessageStatus.PENDING.value,
            "created_at": now,
            "sent_at": None,
            "delivered_at": None,
            "read_at": None,
            "failed_at": None,
            "error_message": None,
            "reply_to_wamid": payload.reply_to_wamid,
        }

        result = await messages.insert_one(message_doc)

        await conversations.update_one(
            {
                "_id": object_id,
            },
            {
                "$set": {
                    "status": ConversationStatus.OPEN.value,
                    "last_message_text": payload.text_body,
                    "last_message_at": now,
                    "updated_at": now,
                }
            },
        )

        saved_message = await messages.find_one({"_id": result.inserted_id})

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    url=settings.N8N_SEND_HUMAN_REPLY_WEBHOOK,
                    json={
                        "mongo_id": str(result.inserted_id),
                        "country_code": conversation['country_code'],
                        "phone": conversation['customer_phone'],
                        "text_message": payload.text_body
                    }
                )
        except Exception as e:
            print("Webhook call Failed: ", e)
            pass

        return WhatsappInboxController._message_to_response(saved_message)

    @staticmethod
    async def update_message_status(payload: UpdateMessageStatus,db) -> WhatsappMessageResponse:
        messages = db[WhatsappInboxController.MESSAGES_COLLECTION]

        query: dict[str, Any] = {}
        if payload.mongo_id:
            query['_id'] = ObjectId(payload.mongo_id) 
        elif payload.wamid:
            query['wamid'] = payload.wamid
        else:
            raise HTTPException(
                status_code=400,
                detail="Mongo ID or Wamid is required"
            )

        message = await messages.find_one(query)

        if not message:
            raise HTTPException(
                status_code=404,
                detail="Message not found",
            )

        status_time = (
            payload.status_timestamp
            or WhatsappInboxController._now()
        )

        update_data: dict[str, Any] = {
            "status": payload.status.value,
        }

        if payload.wamid:
            update_data['wamid'] = payload.wamid

        if payload.status == MessageStatus.SENT:
            update_data["sent_at"] = status_time
        elif payload.status == MessageStatus.DELIVERED:
            update_data["delivered_at"] = status_time
        elif payload.status == MessageStatus.READ:
            update_data["read_at"] = status_time
            update_data["unread_count"] = 0
        elif payload.status == MessageStatus.FAILED:
            update_data["failed_at"] = status_time
            update_data["error_message"] = payload.error_message

        await messages.update_one(
            {
                "_id": message["_id"],
            },
            {
                "$set": update_data,
            },
        )

        updated_message = await messages.find_one({"_id": message["_id"]})
        return WhatsappInboxController._message_to_response(updated_message)

    @staticmethod
    async def update_conversation_status(conversation_id: str,payload: UpdateConversationStatus,db) -> WhatsappConversationResponse:
        conversations = db[WhatsappInboxController.CONVERSATIONS_COLLECTION]
        object_id = WhatsappInboxController._get_object_id(conversation_id)
        result = await conversations.update_one(
            {
                "_id": object_id,
            },
            {
                "$set": {
                    "status": payload.status.value,
                    "updated_at": WhatsappInboxController._now(),
                }
            },
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        updated_conversation = await conversations.find_one({"_id": object_id})
        return WhatsappInboxController._conversation_to_response(updated_conversation)

    @staticmethod
    async def mark_conversation_read(conversation_id: str, db) -> WhatsappConversationResponse:
        conversations = db[WhatsappInboxController.CONVERSATIONS_COLLECTION]
        object_id = WhatsappInboxController._get_object_id(conversation_id)
        result = await conversations.update_one(
            {
                "_id": object_id,
            },
            {
                "$set": {
                    "unread_count": 0,
                    "updated_at": WhatsappInboxController._now(),
                }
            },
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found",
            )

        updated_conversation = await conversations.find_one({"_id": object_id,})

        return WhatsappInboxController._conversation_to_response(
            updated_conversation
        )
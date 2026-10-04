from __future__ import annotations

from dataclasses import dataclass

from app.clients.ai_client import CodysseyAIClient
from app.config import Settings
from app.firebase import create_firestore_client
from app.repositories.conversation_repository import FirestoreConversationRepository
from app.repositories.data_repository import FirestoreDataRepository
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.data_service import DataService
from app.services.summary_service import SummaryService


@dataclass(frozen=True)
class Services:
    data_service: DataService
    summary_service: SummaryService
    conversation_service: ConversationService
    chat_service: ChatService


def build_services(settings: Settings) -> Services:
    firestore_client = create_firestore_client(
        settings.firebase_service_account_file
    )
    data_service = DataService(FirestoreDataRepository(firestore_client))
    summary_service = SummaryService(data_service)
    conversation_service = ConversationService(
        FirestoreConversationRepository(firestore_client)
    )
    chat_service = ChatService(
        summary_service,
        conversation_service,
        CodysseyAIClient(settings),
    )
    return Services(
        data_service=data_service,
        summary_service=summary_service,
        conversation_service=conversation_service,
        chat_service=chat_service,
    )

from __future__ import annotations

from typing import Any, Protocol

from firebase_admin import firestore

from app.schemas.conversations import Conversation, ConversationMessage


class ConversationRepository(Protocol):
    def create(self, title: str, messages: list[ConversationMessage]) -> Conversation: ...

    def list(self) -> list[Conversation]: ...

    def get(self, conversation_id: str) -> Conversation | None: ...

    def delete(self, conversation_id: str) -> bool: ...

    def append_exchange(
        self,
        conversation_id: str,
        user_message: ConversationMessage,
        assistant_message: ConversationMessage,
    ) -> Conversation | None: ...


class FirestoreConversationRepository:
    def __init__(self, client: Any) -> None:
        self.client = client
        self.collection = client.collection("conversations")

    @staticmethod
    def _record(snapshot: Any) -> Conversation:
        return Conversation(id=snapshot.id, **snapshot.to_dict())

    def create(self, title: str, messages: list[ConversationMessage]) -> Conversation:
        reference = self.collection.document()
        reference.set(
            {
                "title": title,
                "messages": [message.model_dump() for message in messages],
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
        )
        created = self.get(reference.id)
        if created is None:
            raise RuntimeError("Firestore did not return the created conversation")
        return created

    def list(self) -> list[Conversation]:
        query = self.collection.order_by(
            "updated_at", direction=firestore.Query.DESCENDING
        )
        return [self._record(snapshot) for snapshot in query.stream()]

    def get(self, conversation_id: str) -> Conversation | None:
        snapshot = self.collection.document(conversation_id).get()
        return self._record(snapshot) if snapshot.exists else None

    def delete(self, conversation_id: str) -> bool:
        reference = self.collection.document(conversation_id)
        transaction = self.client.transaction()

        @firestore.transactional
        def delete_in_transaction(active_transaction: Any) -> bool:
            if not reference.get(transaction=active_transaction).exists:
                return False
            active_transaction.delete(reference)
            return True

        return delete_in_transaction(transaction)

    def append_exchange(
        self,
        conversation_id: str,
        user_message: ConversationMessage,
        assistant_message: ConversationMessage,
    ) -> Conversation | None:
        reference = self.collection.document(conversation_id)
        transaction = self.client.transaction()

        @firestore.transactional
        def append_in_transaction(active_transaction: Any) -> bool:
            snapshot = reference.get(transaction=active_transaction)
            if not snapshot.exists:
                return False
            payload = snapshot.to_dict()
            messages = payload.get("messages", []) + [
                user_message.model_dump(),
                assistant_message.model_dump(),
            ]
            active_transaction.update(
                reference,
                {
                    "messages": messages,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
            )
            return True

        if not append_in_transaction(transaction):
            return None
        return self.get(conversation_id)

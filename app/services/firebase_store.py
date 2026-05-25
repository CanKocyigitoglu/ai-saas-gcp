import os
from datetime import datetime
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore
from google.api_core.exceptions import GoogleAPIError, NotFound


def _get_collection_name() -> str:
    return os.getenv("FIREBASE_OUTPUT_COLLECTION", "model_outputs")


def get_firestore_client():
    """
    Initialise Firebase Admin SDK once and return a Firestore client.
    Uses GOOGLE_APPLICATION_CREDENTIALS when provided.
    """
    if not firebase_admin._apps:
        project_id = os.getenv("FIREBASE_PROJECT_ID")
        credential_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        options = {"projectId": project_id} if project_id else None

        if credential_path and os.path.exists(credential_path):
            cred = credentials.Certificate(credential_path)
            firebase_admin.initialize_app(cred, options=options)
        else:
            firebase_admin.initialize_app(options=options)

    return firestore.client()


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_json_safe(item) for item in value]

    return value


def _document_to_dict(snapshot) -> dict[str, Any] | None:
    if snapshot is None or not snapshot.exists:
        return None

    data = snapshot.to_dict()
    data = _json_safe(data)
    data["id"] = snapshot.id
    return data


def save_model_output(
    request_type: str,
    input_summary: str | None,
    model: str | None,
    output: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    source_interaction_id: int | None = None,
) -> dict[str, Any]:
    """
    Create a Firestore document for a model output.
    """
    try:
        db = get_firestore_client()
        doc_ref = db.collection(_get_collection_name()).document()

        payload = {
            "request_type": request_type,
            "input_summary": input_summary,
            "model": model,
            "output": output,
            "metadata": metadata or {},
            "source_interaction_id": source_interaction_id,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }

        doc_ref.set(payload)
        snapshot = doc_ref.get()
        result = _document_to_dict(snapshot)

        if result is None:
            raise RuntimeError("Created Firestore document could not be read.")

        return result

    except GoogleAPIError as exc:
        raise RuntimeError(f"Firestore save failed: {exc}") from exc


def list_model_outputs(
    limit: int = 50,
    request_type: str | None = None,
) -> list[dict[str, Any]]:
    """
    List recent model outputs from Firestore.
    Filtering is done in Python to avoid requiring composite indexes during development.
    """
    try:
        db = get_firestore_client()

        stream_limit = min(limit * 5 if request_type else limit, 200)

        docs = (
            db.collection(_get_collection_name())
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(stream_limit)
            .stream()
        )

        items = []

        for doc in docs:
            item = _document_to_dict(doc)

            if item is None:
                continue

            if request_type and item.get("request_type") != request_type:
                continue

            items.append(item)

            if len(items) >= limit:
                break

        return items

    except GoogleAPIError as exc:
        raise RuntimeError(f"Firestore list failed: {exc}") from exc


def get_model_output(document_id: str) -> dict[str, Any] | None:
    try:
        db = get_firestore_client()
        snapshot = db.collection(_get_collection_name()).document(document_id).get()
        return _document_to_dict(snapshot)

    except GoogleAPIError as exc:
        raise RuntimeError(f"Firestore get failed: {exc}") from exc


def update_model_output(
    document_id: str,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        db = get_firestore_client()
        doc_ref = db.collection(_get_collection_name()).document(document_id)

        snapshot = doc_ref.get()

        if not snapshot.exists:
            return None

        update_data = {
            key: value
            for key, value in updates.items()
            if value is not None
        }

        update_data["updated_at"] = firestore.SERVER_TIMESTAMP

        doc_ref.update(update_data)

        return get_model_output(document_id)

    except NotFound:
        return None
    except GoogleAPIError as exc:
        raise RuntimeError(f"Firestore update failed: {exc}") from exc


def delete_model_output(document_id: str) -> bool:
    try:
        db = get_firestore_client()
        doc_ref = db.collection(_get_collection_name()).document(document_id)

        snapshot = doc_ref.get()

        if not snapshot.exists:
            return False

        doc_ref.delete()
        return True

    except GoogleAPIError as exc:
        raise RuntimeError(f"Firestore delete failed: {exc}") from exc


def _get_postprocess_collection_name() -> str:
    return os.getenv("FIREBASE_POSTPROCESS_COLLECTION", "postprocessed_outputs")


def save_postprocessed_output(
    job_id: str,
    request_type: str,
    input_summary: str | None,
    model: str | None,
    firebase_output_id: str | None,
    source_interaction_id: int | None,
    original_output: dict[str, Any],
    processed_output: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Save a post-processed output document in Firestore.
    """
    try:
        db = get_firestore_client()
        doc_ref = db.collection(_get_postprocess_collection_name()).document(job_id)

        payload = {
            "job_id": job_id,
            "request_type": request_type,
            "input_summary": input_summary,
            "model": model,
            "firebase_output_id": firebase_output_id,
            "source_interaction_id": source_interaction_id,
            "original_output": original_output,
            "processed_output": processed_output,
            "metadata": metadata or {},
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }

        doc_ref.set(payload)
        snapshot = doc_ref.get()
        result = _document_to_dict(snapshot)

        if result is None:
            raise RuntimeError("Created Firestore postprocess document could not be read.")

        return result

    except GoogleAPIError as exc:
        raise RuntimeError(f"Firestore postprocess save failed: {exc}") from exc


def list_postprocessed_outputs(
    limit: int = 50,
    request_type: str | None = None,
) -> list[dict[str, Any]]:
    try:
        db = get_firestore_client()

        stream_limit = min(limit * 5 if request_type else limit, 200)

        docs = (
            db.collection(_get_postprocess_collection_name())
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(stream_limit)
            .stream()
        )

        items = []

        for doc in docs:
            item = _document_to_dict(doc)

            if item is None:
                continue

            if request_type and item.get("request_type") != request_type:
                continue

            items.append(item)

            if len(items) >= limit:
                break

        return items

    except GoogleAPIError as exc:
        raise RuntimeError(f"Firestore postprocess list failed: {exc}") from exc


def get_postprocessed_output(job_id: str) -> dict[str, Any] | None:
    try:
        db = get_firestore_client()
        snapshot = db.collection(_get_postprocess_collection_name()).document(job_id).get()
        return _document_to_dict(snapshot)

    except GoogleAPIError as exc:
        raise RuntimeError(f"Firestore postprocess get failed: {exc}") from exc

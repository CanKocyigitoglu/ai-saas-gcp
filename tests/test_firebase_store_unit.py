from datetime import datetime, timezone

from app.services import firebase_store


FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeSnapshot:
    def __init__(self, doc_id, data=None):
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data)


class FakeDocumentRef:
    def __init__(self, collection, doc_id):
        self.collection = collection
        self.id = doc_id

    def _normalise(self, payload):
        data = dict(payload)

        for key in ("created_at", "updated_at"):
            if key in data:
                data[key] = FIXED_TIME

        return data

    def set(self, payload):
        self.collection.store[self.id] = self._normalise(payload)

    def get(self):
        return FakeSnapshot(self.id, self.collection.store.get(self.id))

    def update(self, updates):
        current = self.collection.store[self.id]
        current.update(self._normalise(updates))

    def delete(self):
        self.collection.store.pop(self.id, None)


class FakeCollection:
    def __init__(self):
        self.store = {}
        self._limit = None

    def document(self, doc_id=None):
        doc_id = doc_id or f"doc-{len(self.store) + 1}"
        return FakeDocumentRef(self, doc_id)

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, value):
        self._limit = value
        return self

    def stream(self):
        items = list(self.store.items())

        if self._limit is not None:
            items = items[: self._limit]

        for doc_id, data in items:
            yield FakeSnapshot(doc_id, data)


class FakeFirestore:
    def __init__(self):
        self.collections = {}

    def collection(self, name):
        self.collections.setdefault(name, FakeCollection())
        return self.collections[name]


def test_json_safe_converts_datetime_to_isoformat():
    value = firebase_store._json_safe({"created_at": FIXED_TIME})

    assert value["created_at"] == FIXED_TIME.isoformat()


def test_document_to_dict_returns_none_for_missing_snapshot():
    snapshot = FakeSnapshot("missing", None)

    assert firebase_store._document_to_dict(snapshot) is None


def test_firebase_model_output_crud(monkeypatch):
    fake_db = FakeFirestore()

    monkeypatch.setattr(firebase_store, "get_firestore_client", lambda: fake_db)
    monkeypatch.setattr(firebase_store, "_get_collection_name", lambda: "model_outputs")

    created = firebase_store.save_model_output(
        request_type="manual",
        input_summary="manual test",
        model="test-model",
        output={"result": "ok"},
        metadata={"stage": "unit-test"},
    )

    doc_id = created["id"]
    assert created["request_type"] == "manual"

    fetched = firebase_store.get_model_output(doc_id)
    assert fetched["id"] == doc_id
    assert fetched["output"]["result"] == "ok"

    listed = firebase_store.list_model_outputs(limit=10)
    assert len(listed) == 1
    assert listed[0]["id"] == doc_id

    updated = firebase_store.update_model_output(
        doc_id,
        {"metadata": {"reviewed": True}},
    )
    assert updated["metadata"]["reviewed"] is True

    assert firebase_store.delete_model_output(doc_id) is True
    assert firebase_store.get_model_output(doc_id) is None


def test_firebase_postprocessed_output_save_and_get(monkeypatch):
    fake_db = FakeFirestore()

    monkeypatch.setattr(firebase_store, "get_firestore_client", lambda: fake_db)
    monkeypatch.setattr(firebase_store, "_get_postprocess_collection_name", lambda: "postprocessed_outputs")

    saved = firebase_store.save_postprocessed_output(
        job_id="job-123",
        request_type="image",
        input_summary="traffic.png",
        model="ecowaste-yolo-taco-best",
        firebase_output_id="firebase-doc-1",
        source_interaction_id=1,
        original_output={"predictions": []},
        processed_output={"summary": "No objects were detected."},
        metadata={"worker": "unit-test"},
    )

    assert saved["id"] == "job-123"
    assert saved["processed_output"]["summary"] == "No objects were detected."

    fetched = firebase_store.get_postprocessed_output("job-123")
    assert fetched["job_id"] == "job-123"

    listed = firebase_store.list_postprocessed_outputs(limit=5)
    assert len(listed) == 1

import io
import pytest
from fastapi.testclient import TestClient
from fastapi import status
from bson import ObjectId
from datetime import datetime

from api.routes.context import router
from api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_dependencies(mocker):
    # Mock verify_token to always return a fake user
    mocker.patch("api.routes.context.verify_token", return_value={"organization": str(ObjectId())})

    # Mock DBs
    mock_agents_db = mocker.Mock()
    mock_knowledge_db = mocker.Mock()

    # Ensure find_one returns a proper dictionary for knowledge_db
    mock_knowledge_db.find_one.return_value = {
        "_id": ObjectId(),
        "file_key": "some_file_key",
        "is_tabular": False,
        "structured_data": None,
        "created_at": datetime.utcnow(),
    }

    mocker.patch("api.routes.context.agents_db", mock_agents_db)
    mocker.patch("api.routes.context.knowledge_db", mock_knowledge_db)

    # Mock embeddings
    mocker.patch("api.routes.context.embed", return_value=["chunk1", "chunk2"])
    mocker.patch("api.routes.context.save_embedding", return_value=ObjectId())
    mocker.patch("api.routes.context.get_embeddings", return_value={"content": "mocked embedding"})

    # Mock minio_client.put_object to avoid real MinIO connection
    mock_minio_client = mocker.patch("api.routes.context.minio_client")
    mock_minio_client.put_object = mocker.Mock(return_value=None)

    return {
        "agents_db": mock_agents_db,
        "knowledge_db": mock_knowledge_db,
        "minio_client": mock_minio_client,
    }


def test_list_context_entries_success(mock_dependencies):
    agent_id = str(ObjectId())
    context_ids = [ObjectId(), ObjectId()]
    mock_dependencies["agents_db"].find_one.return_value = {
        "_id": ObjectId(agent_id),
        "context": context_ids,
        "file_key": "agent_file_key",
        "is_tabular": False,
        "structured_data": None,
        "created_at": datetime.utcnow(),
    }

    response = client.get(f"/agents/{agent_id}/context", headers={"Authorization": "Bearer testtoken"})
    assert response.status_code == 200

    json_response = response.json()
    assert isinstance(json_response, list)
    # Check that each entry contains the expected keys
    for entry in json_response:
        assert "context_id" in entry
        assert "file_key" in entry
        assert "filename" in entry
        assert "is_tabular" in entry
        assert "structured_data" in entry
        assert "created_at" in entry


def test_get_context_entry_success(mock_dependencies):
    agent_id = str(ObjectId())
    context_id = ObjectId()
    mock_dependencies["agents_db"].find_one.return_value = {
        "_id": ObjectId(agent_id),
        "context": [context_id],
        "file_key": "agent_file_key",
        "is_tabular": False,
        "structured_data": None,
        "created_at": datetime.utcnow(),
    }
    mock_dependencies["knowledge_db"].find_one.return_value = {
        "_id": context_id,
        "file_key": "some_file_key",
        "is_tabular": False,
        "structured_data": None,
        "created_at": datetime.utcnow(),
    }
    # get_embeddings is mocked to return {"content": "mocked embedding"}

    response = client.get(f"/agents/{agent_id}/context/{str(context_id)}", headers={"Authorization": "Bearer testtoken"})

    assert response.status_code == 200
    assert response.json()["content"] == "mocked embedding"


def test_get_ingested_content_success(mock_dependencies):
    agent_id = str(ObjectId())
    context_id = ObjectId()
    mock_dependencies["agents_db"].find_one.return_value = {
        "_id": ObjectId(agent_id),
        "context": [context_id],
        "file_key": "agent_file_key",
        "is_tabular": False,
        "structured_data": None,
        "created_at": datetime.utcnow(),
    }
    mock_dependencies["knowledge_db"].find_one.return_value = {
        "_id": context_id,
        "file_key": "some_file_key",
        "is_tabular": True,
        "structured_data": {"data": "mocked structured data"},
        "created_at": datetime.utcnow(),
        "chunks": ["chunk1", "chunk2"],
    }

    response = client.get(f"/agents/{agent_id}/context/{str(context_id)}/ingested_content", headers={"Authorization": "Bearer testtoken"})

    assert response.status_code == 200
    assert "ingested_content" in response.json()


def test_upload_context_file_success(mock_dependencies, mocker):
    agent_id = str(ObjectId())
    mock_dependencies["agents_db"].find_one.return_value = {
        "_id": ObjectId(agent_id),
        "context": [],
        "file_key": "agent_file_key",
        "is_tabular": False,
        "structured_data": None,
        "created_at": datetime.utcnow(),
    }

    # Patch PyPDF2.PdfReader to return a mock reader with one page whose extract_text returns "hello"
    class MockPage:
        def extract_text(self):
            return "hello"

    class MockReader:
        pages = [MockPage()]

    mocker.patch("PyPDF2.PdfReader", return_value=MockReader())

    # Use a minimal valid PDF header (reader is mocked anyway)
    pdf_buffer = io.BytesIO(b"%PDF-1.4\n%EOF\n")

    response = client.post(
        f"/agents/{agent_id}/context",
        headers={"Authorization": "Bearer testtoken"},
        files={"file": ("test.pdf", pdf_buffer, "application/pdf")},
    )

    assert response.status_code == 201
    assert "context_id" in response.json()


def test_upload_context_file_invalid_type(mock_dependencies):
    agent_id = str(ObjectId())
    mock_dependencies["agents_db"].find_one.return_value = {
        "_id": ObjectId(agent_id),
        "context": [],
        "file_key": "agent_file_key",
        "is_tabular": False,
        "structured_data": None,
        "created_at": datetime.utcnow(),
    }

    response = client.post(
        f"/agents/{agent_id}/context",
        headers={"Authorization": "Bearer testtoken"},
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type."


def test_delete_context_entry_success(mock_dependencies, mocker):
    agent_id = str(ObjectId())
    context_id = ObjectId()

    mock_dependencies["agents_db"].find_one.return_value = {
        "_id": ObjectId(agent_id),
        "context": [context_id],
        "file_key": "agent_file_key",
        "is_tabular": False,
        "structured_data": None,
        "created_at": datetime.utcnow(),
    }
    mock_dependencies["knowledge_db"].find_one.return_value = {
        "_id": context_id,
        "file_key": "some_file_key",
        "is_tabular": False,
        "structured_data": None,
        "created_at": datetime.utcnow(),
    }
    mock_delete_result = mocker.Mock()
    mock_delete_result.deleted_count = 1
    mock_dependencies["knowledge_db"].delete_one.return_value = mock_delete_result

    response = client.delete(
        f"/agents/{agent_id}/context/{str(context_id)}", headers={"Authorization": "Bearer testtoken"}
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Context Entry Deleted successfully"
import io
import pytest
from fastapi.testclient import TestClient
from fastapi import status
from bson import ObjectId

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
    mocker.patch("api.routes.context.agents_db", mock_agents_db)
    mocker.patch("api.routes.context.knowledge_db", mock_knowledge_db)

    # Mock embeddings
    mocker.patch("api.routes.context.embed", return_value=["chunk1", "chunk2"])
    mocker.patch("api.routes.context.save_embedding", return_value=ObjectId())
    mocker.patch("api.routes.context.get_embeddings", return_value={"content": "mocked embedding"})

    return {
        "agents_db": mock_agents_db,
        "knowledge_db": mock_knowledge_db,
    }


def test_list_context_entries_success(mock_dependencies):
    agent_id = str(ObjectId())
    context_data = {"documents": [str(ObjectId()), str(ObjectId())]}
    mock_dependencies["agents_db"].find_one.return_value = {"_id": ObjectId(agent_id), "context": context_data}

    response = client.get(f"/agents/{agent_id}/context", headers={"Authorization": "Bearer testtoken"})

    assert response.status_code == 200
    assert "documents" in response.json()
    assert isinstance(response.json()["documents"], list)


def test_get_context_entry_success(mock_dependencies):
    agent_id = str(ObjectId())
    context_id = str(ObjectId())
    mock_dependencies["agents_db"].find_one.return_value = {"_id": ObjectId(agent_id), "context": [ObjectId(context_id)]}

    response = client.get(f"/agents/{agent_id}/context/{context_id}", headers={"Authorization": "Bearer testtoken"})

    assert response.status_code == 200
    assert response.json()["content"] == "mocked embedding"


def test_get_ingested_content_success(mock_dependencies):
    agent_id = str(ObjectId())
    context_id = str(ObjectId())
    mock_dependencies["agents_db"].find_one.return_value = {"_id": ObjectId(agent_id), "context": [ObjectId(context_id)]}
    mock_dependencies["knowledge_db"].find_one.return_value = {"_id": ObjectId(context_id), "chunks": ["chunk1", "chunk2"]}

    response = client.get(f"/agents/{agent_id}/context/{context_id}/ingested_content", headers={"Authorization": "Bearer testtoken"})

    assert response.status_code == 200
    assert "ingested_content" in response.json()


def test_upload_context_file_success(mock_dependencies, mocker):
    agent_id = str(ObjectId())
    mock_dependencies["agents_db"].find_one.return_value = {"_id": ObjectId(agent_id), "context": []}

    # Patch PyPDF2.PdfReader to return a mock reader with one page whose extract_text returns "hello"
    mock_page = type("MockPage", (), {"extract_text": lambda self: "hello"})()
    mock_reader = type("MockReader", (), {"pages": [mock_page]})()
    import PyPDF2
    import sys
    sys.modules["PyPDF2"] = PyPDF2
    # Use mocker to patch
    import pytest
    pytest.MonkeyPatch().setattr("PyPDF2.PdfReader", lambda _: mock_reader)

    # Mock minio_client.put_object to avoid real MinIO connection
    mock_minio_client = mocker.patch("api.routes.context.minio_client")
    mock_minio_client.put_object = mocker.Mock(return_value=None)

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
    mock_dependencies["agents_db"].find_one.return_value = {"_id": ObjectId(agent_id), "context": []}

    response = client.post(
        f"/agents/{agent_id}/context",
        headers={"Authorization": "Bearer testtoken"},
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type."


def test_delete_context_entry_success(mock_dependencies):
    agent_id = str(ObjectId())
    context_id = str(ObjectId())

    mock_dependencies["agents_db"].find_one.return_value = {"_id": ObjectId(agent_id), "context": [ObjectId(context_id)]}
    mock_dependencies["knowledge_db"].find_one.return_value = {"_id": ObjectId(context_id)}
    mock_dependencies["knowledge_db"].delete_one.return_value.deleted_count = 1

    response = client.delete(
        f"/agents/{agent_id}/context/{context_id}", headers={"Authorization": "Bearer testtoken"}
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Context Entry Deleted successfully"
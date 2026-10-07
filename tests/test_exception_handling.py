def test_unsupported_file_extension(client, tmp_path):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("Hello world", encoding="utf-8")

    with open(txt_file, "rb") as f:
        resp = client.post(
            "/api/files/",
            files={"file": ("notes.txt", f, "text/plain")},
        )

    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert "Unsupported file type" in data["error"]["message"]


def test_corrupted_zip_file(client, tmp_path):
    bad_zip = tmp_path / "corrupted.zip"
    bad_zip.write_bytes(b"This is not a zip file content at all")

    with open(bad_zip, "rb") as f:
        resp = client.post(
            "/api/files/",
            files={"file": ("corrupted.zip", f, "application/zip")},
        )

    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "CORRUPTED_FILE"


def test_missing_shapefile_components(client, incomplete_shapefile_zip):
    with open(incomplete_shapefile_zip, "rb") as f:
        resp = client.post(
            "/api/files/",
            files={"file": ("incomplete.zip", f, "application/zip")},
        )

    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "MISSING_SHAPEFILE_COMPONENTS"
    assert ".dbf" in data["error"]["message"]


def test_zipslip_traversal_attack_blocked(client, malicious_zipslip_zip):
    with open(malicious_zipslip_zip, "rb") as f:
        resp = client.post(
            "/api/files/",
            files={"file": ("zipslip.zip", f, "application/zip")},
        )

    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "ZIP_SLIP_ATTEMPT"


def test_nonexistent_file_id_returns_404(client):
    resp = client.get("/api/files/non-existent-uuid-12345/")
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"]["code"] == "FILE_NOT_FOUND"


def test_health_check_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "supported_drivers" in data

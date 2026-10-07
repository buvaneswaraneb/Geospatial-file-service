def test_upload_kml_file_success(client, sample_kml_file):
    with open(sample_kml_file, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("survey.kml", f, "application/vnd.google-earth.kml+xml")},
        )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "survey.kml"
    assert data["feature_count"] == 3
    assert data["status"] == "COMPLETED"
    assert "EPSG:4326" in data["crs"]


def test_upload_shapefile_zip_success(client, sample_shapefile_zip):
    with open(sample_shapefile_zip, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("parcels.zip", f, "application/zip")},
        )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "parcels.zip"
    assert data["feature_count"] == 2
    assert data["status"] == "COMPLETED"


def test_get_file_information(client, sample_kml_file):
    # Upload first
    with open(sample_kml_file, "rb") as f:
        upload_resp = client.post(
            "/api/files/",
            files={"file": ("survey.kml", f, "application/vnd.google-earth.kml+xml")},
        )
    file_id = upload_resp.json()["id"]

    # Get info
    get_resp = client.get(f"/api/files/{file_id}/")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == file_id
    assert data["filename"] == "survey.kml"
    assert data["feature_count"] == 3
    assert data["status"] == "COMPLETED"
    assert "EPSG:4326" in data["crs"]


def test_list_files(client, sample_kml_file):
    # Upload
    with open(sample_kml_file, "rb") as f:
        client.post(
            "/api/files/",
            files={"file": ("survey.kml", f, "application/vnd.google-earth.kml+xml")},
        )

    list_resp = client.get("/api/files/")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_get_file_features(client, sample_kml_file):
    with open(sample_kml_file, "rb") as f:
        upload_resp = client.post(
            "/api/files/",
            files={"file": ("survey.kml", f, "application/vnd.google-earth.kml+xml")},
        )
    file_id = upload_resp.json()["id"]

    feat_resp = client.get(f"/api/files/{file_id}/features/")
    assert feat_resp.status_code == 200
    data = feat_resp.json()
    assert data["total"] == 3
    assert len(data["features"]) == 3
    assert data["features"][0]["geometry"]["type"] == "Polygon"


def test_delete_file(client, sample_kml_file):
    with open(sample_kml_file, "rb") as f:
        upload_resp = client.post(
            "/api/files/",
            files={"file": ("survey.kml", f, "application/vnd.google-earth.kml+xml")},
        )
    file_id = upload_resp.json()["id"]

    # Delete
    del_resp = client.delete(f"/api/files/{file_id}/")
    assert del_resp.status_code == 204

    # Get should be 404
    get_resp = client.get(f"/api/files/{file_id}/")
    assert get_resp.status_code == 404

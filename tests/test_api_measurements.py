def test_get_file_measurements_details(client, sample_kml_file):
    # Upload sample KML which has 1 Polygon, 1 LineString, 1 Point
    with open(sample_kml_file, "rb") as f:
        upload_resp = client.post(
            "/api/files/",
            files={"file": ("survey.kml", f, "application/vnd.google-earth.kml+xml")},
        )
    assert upload_resp.status_code == 201
    file_id = upload_resp.json()["id"]

    measurements_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert measurements_resp.status_code == 200
    data = measurements_resp.json()

    # Check Summary
    summary = data["summary"]
    assert summary["total_features"] == 3
    assert summary["polygons_measured"] == 1
    assert summary["lines_measured"] == 1
    assert summary["points_skipped"] == 1
    assert summary["unsupported_geometries"] == 0
    assert summary["total_area_sq_meters"] > 1_000_000
    assert summary["total_length_meters"] > 1_000

    # Check Individual measurements
    items = data["measurements"]
    assert len(items) == 3

    # Feature 0: Polygon
    poly_item = items[0]
    assert poly_item["geometry_type"] == "Polygon"
    assert poly_item["measurement_type"] == "AREA"
    assert poly_item["units"] == "square_meters"
    assert poly_item["value"] > 1_000_000
    assert "area_sq_km" in poly_item["additional_metrics"]
    assert "area_hectares" in poly_item["additional_metrics"]
    assert "EPSG:32643" in poly_item["projected_crs"] or "32643" in poly_item["projected_crs"]

    # Feature 1: LineString
    line_item = items[1]
    assert line_item["geometry_type"] == "LineString"
    assert line_item["measurement_type"] == "LENGTH"
    assert line_item["units"] == "meters"
    assert line_item["value"] > 1_000
    assert "length_km" in line_item["additional_metrics"]

    # Feature 2: Point (must be skipped gracefully per requirements)
    point_item = items[2]
    assert point_item["geometry_type"] == "Point"
    assert point_item["measurement_type"] == "NONE"
    assert point_item["value"] is None
    assert "no measurement required" in point_item["notes"].lower()


def test_shapefile_measurements(client, sample_shapefile_zip):
    with open(sample_shapefile_zip, "rb") as f:
        upload_resp = client.post(
            "/api/files/",
            files={"file": ("parcels.zip", f, "application/zip")},
        )
    assert upload_resp.status_code == 201
    file_id = upload_resp.json()["id"]

    measurements_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert measurements_resp.status_code == 200
    data = measurements_resp.json()

    assert data["summary"]["total_features"] == 2
    assert data["summary"]["polygons_measured"] == 2
    assert data["summary"]["lines_measured"] == 0
    assert data["summary"]["total_area_sq_meters"] > 2_000_000

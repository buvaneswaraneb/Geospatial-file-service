import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Generator
import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Polygon
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Use isolated test database
TEST_DB_PATH = Path("./test_geospatial.db")
test_engine = create_engine(
    f"sqlite:///{TEST_DB_PATH}",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    settings.UPLOAD_DIR = Path("./test_uploads")
    settings.DATA_DIR = Path("./test_data")
    settings.ensure_directories()
    yield
    # Cleanup
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass
    if settings.UPLOAD_DIR.exists():
        shutil.rmtree(settings.UPLOAD_DIR, ignore_errors=True)
    if settings.DATA_DIR.exists():
        shutil.rmtree(settings.DATA_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_database():
    """Reset database tables before each test for complete test isolation."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_kml_content() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Sample Geospatial Survey</name>
    <Placemark>
      <name>Survey Park</name>
      <description>Public park area</description>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.5900,12.9700,0
              77.6000,12.9700,0
              77.6000,12.9800,0
              77.5900,12.9800,0
              77.5900,12.9700,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    <Placemark>
      <name>Main Highway</name>
      <description>Highway connecting sector 1 and 2</description>
      <LineString>
        <coordinates>
          77.5900,12.9700,0
          77.6100,12.9800,0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Benchmark Station</name>
      <description>Survey beacon</description>
      <Point>
        <coordinates>
          77.5950,12.9750,0
        </coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>"""


@pytest.fixture
def sample_kml_file(tmp_path, sample_kml_content) -> Path:
    kml_path = tmp_path / "survey.kml"
    kml_path.write_text(sample_kml_content, encoding="utf-8")
    return kml_path


@pytest.fixture
def sample_shapefile_zip(tmp_path) -> Path:
    # Create GeoDataFrame with two polygons (ESRI Shapefile requires homogeneous geometry type)
    poly1 = Polygon([(77.59, 12.97), (77.60, 12.97), (77.60, 12.98), (77.59, 12.98), (77.59, 12.97)])
    poly2 = Polygon([(77.61, 12.97), (77.62, 12.97), (77.62, 12.98), (77.61, 12.98), (77.61, 12.97)])
    gdf = gpd.GeoDataFrame(
        [
            {"name": "Parcel 1", "category": "Commercial", "geometry": poly1},
            {"name": "Parcel 2", "category": "Residential", "geometry": poly2},
        ],
        crs="EPSG:4326",
    )

    shp_dir = tmp_path / "shp_src"
    shp_dir.mkdir()
    shp_base = shp_dir / "parcels.shp"
    gdf.to_file(shp_base)

    zip_path = tmp_path / "parcels.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
            candidate = shp_dir / f"parcels{ext}"
            if candidate.exists():
                zf.write(candidate, arcname=f"parcels{ext}")

    return zip_path


@pytest.fixture
def incomplete_shapefile_zip(tmp_path) -> Path:
    """Shapefile ZIP missing the required .dbf component."""
    zip_path = tmp_path / "incomplete.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("test.shp", "dummy content")
        zf.writestr("test.shx", "dummy content")
        # Missing .dbf
    return zip_path


@pytest.fixture
def malicious_zipslip_zip(tmp_path) -> Path:
    """ZIP containing ZipSlip path traversal member."""
    zip_path = tmp_path / "zipslip.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../malicious.txt", "exploit")
    return zip_path

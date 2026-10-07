import os
import tempfile
import zipfile
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Polygon

SAMPLES_DIR = Path("./samples")
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

# 1. Generate sample KML
kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Bengaluru City Survey</name>
    <Placemark>
      <name>Cubbon Park Boundary</name>
      <description>Heritage park located in the heart of Bengaluru</description>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              77.5900,12.9730,0
              77.5960,12.9730,0
              77.5960,12.9780,0
              77.5900,12.9780,0
              77.5900,12.9730,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    <Placemark>
      <name>MG Road Transit Corridor</name>
      <description>Major transit road in Central Bengaluru</description>
      <LineString>
        <coordinates>
          77.5930,12.9750,0
          77.6080,12.9750,0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Vidhana Soudha Landmark</name>
      <description>State legislative building</description>
      <Point>
        <coordinates>
          77.5908,12.9796,0
        </coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>"""

kml_file = SAMPLES_DIR / "sample_survey.kml"
kml_file.write_text(kml_content, encoding="utf-8")
print(f"Created: {kml_file}")

# 2. Generate sample Shapefile .zip
poly1 = Polygon([(77.59, 12.97), (77.60, 12.97), (77.60, 12.98), (77.59, 12.98), (77.59, 12.97)])
poly2 = Polygon([(77.61, 12.97), (77.62, 12.97), (77.62, 12.98), (77.61, 12.98), (77.61, 12.97)])
gdf = gpd.GeoDataFrame(
    [
        {"parcel_id": "P-101", "zone": "Commercial", "owner": "Metro Corp", "geometry": poly1},
        {"parcel_id": "P-102", "zone": "Residential", "owner": "Urban Trust", "geometry": poly2},
    ],
    crs="EPSG:4326",
)

with tempfile.TemporaryDirectory() as tmpdir:
    shp_base = Path(tmpdir) / "land_parcels.shp"
    gdf.to_file(shp_base)

    zip_file = SAMPLES_DIR / "sample_parcels.zip"
    with zipfile.ZipFile(zip_file, "w") as zf:
        for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
            candidate = Path(tmpdir) / f"land_parcels{ext}"
            if candidate.exists():
                zf.write(candidate, arcname=f"land_parcels{ext}")

print(f"Created: {zip_file}")
print("Sample files generation complete!")

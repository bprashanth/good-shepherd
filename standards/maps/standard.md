# Map Visualization Standards

## Overview

This document outlines the standards and practices for working with geospatial site data.
It is a WIP.

## Coordinate Systems

- **Standard**: WGS84 (EPSG:4326)
- **Format**: `[longitude, latitude]` (GeoJSON) or `lon,lat` (KML)
- **Precision**: 6 decimal places for coordinate matching (~0.1m accuracy)

## KML vs Geojson: Context

The fundamental difference is that KML stores “what belongs inside what” in the file itself, while GeoJSON stores “what belongs to what” as data that your software has to interpret. Here is an example

**KML**

```xml
<kml>
  <Document>
    <Folder>
      <name>Tamil Nadu</name>

      <Folder>
        <name>Nilgiris</name>

        <Placemark>
          <name>Site A</name>
          <Point>
            <coordinates>76.7,11.4</coordinates>
          </Point>
        </Placemark>

        <Placemark>
          <name>Site B</name>
          <Point>
            <coordinates>76.8,11.5</coordinates>
          </Point>
        </Placemark>

      </Folder>
    </Folder>
  </Document>
</kml>
```

With this structure, one does not need extra code to understand that Site A and Site B belong within district Nilgiris.

**GeoJSON**

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "state": "Tamil Nadu",
        "district": "Nilgiris",
        "name": "Site A"
      },
      "geometry": {
        "type": "Point",
        "coordinates": [76.7, 11.4]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "state": "Tamil Nadu",
        "district": "Nilgiris",
        "name": "Site B"
      },
      "geometry": {
        "type": "Point",
        "coordinates": [76.8, 11.5]
      }
    }
  ]
}
```

As you can see, the data is not lost between the two. The structure is.
However this structure is easily reconstructed.
To understand which sites belong within a district, one simply has to query `district=Nilgiris`.

While we don't have an explicit preference for one or the other, it is true that many web technologies (databases, mobile apps, apis etc) prefer the latter (or more generally, prefer flat lists and queries instead of embedded structure). Flat lists are typically easier to query, index, merge and process incrementally.

Hence the rest of this document tries to express a loose standard guide for the transfer transformation of kml features to geojson features. While we have not provided every possible feature transformation, we have tried to include the common ones in ecology datasets. If your input dataset has a `kml` with a geometry or feature not explicity recognized by this document, it may or may not get correctly representd in the output geojson - visual inspection and testing might be required.

### Translation Strategy

- **Geometry mapping**:
  - KML `<Point>` = GeoJSON `"type": "Point"`
  - KML `<LineString>` = GeoJSON `"type": "LineString"`
  - KML `<Polygon>` = GeoJSON `"type": "Polygon"`
- **Metadata preservation**:
  - KML `<name>` = GeoJSON `properties.name`
  - KML ExtendedData = GeoJSON `properties.*`
- **Recognized Losses in conversion**:
  - Folder/Document hierarchy (flattened, see example above)
  - Style definitions (converted to simple styling)
  - Camera views (LookAt) - not preserved

#### A note on altitude

Both standards allow

```
[lon, lat, alt]
```

But the treatment of `alt` as the third value in this list is inconsistent across tools. Hence we will explicitly remove it from the `coordinates` field and add it as a property, if present. Eg

```xml
          <Point>
            <coordinates>76.8,11.5,25</coordinates>
          </Point>
```

Becomes

```json
      "properties": {
        "state": "Tamil Nadu",
        "district": "Nilgiris",
        "name": "Site B",
        "altitude": "25m",
        "altitudeMode": "..the value of kml's altitudeMode .."
      },
```

Where per the kml spec, `altitudeMode` could be

1. `clampToGround`: this is simply ignored by our conversion. Per kml spec it means ignore the altitude and only render the trails, but we will not be ignoring the altitude value in conversion.

2. `relativeToGround`: It is typical for eg canopy height - since it means 25m above the ground at that point.

3. `absolute`: meters above sea level.

We assume if a third value is found in the coordinates, it is `relativeToGround` regardless of `altitudeMode`.

#### GeoJSON to KML Conversion (Possibly in the future)

- Reverse mapping of geometry types
- Reconstruct folder structure if metadata available
- Apply default styles

## Label Display Standards

This has nothing to do with the flattening. The main problem to highlight here is many files have overlapping labels for transect and sites causing visual clutter. Ideally we should handle these dynamically, or using hover, or just click layers, making the need for a "standard" unnecessary.

## References

- [KML Specification](https://developers.google.com/kml/documentation/kmlreference)
- [GeoJSON Specification (RFC 7946)](https://tools.ietf.org/html/rfc7946)
- [QGIS Documentation](https://qgis.org/documentation/)

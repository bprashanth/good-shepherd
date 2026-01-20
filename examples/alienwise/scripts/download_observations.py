import argparse
import logging
import json
import csv
import os
import sys
from datetime import datetime, date
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

try:
    from pygbif import occurrences as gbif_occurrences
except ImportError:
    gbif_occurrences = None

try:
    from pyinaturalist import get_observations
except ImportError:
    get_observations = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Constants from documentation
DEFAULT_AOI_BOUNDS = {
    'min_lon': 72.891666666667,
    'max_lon': 78.06666666646001,
    'min_lat': 8.116666666667001,
    'max_lat': 21.266666666141
}

class DataSource(ABC):
    """Abstract base class for data sources."""

    def __init__(self, species_name: str, aoi: Dict[str, float], start_date: str, end_date: str):
        self.species_name = species_name
        self.aoi = aoi
        self.start_date = start_date
        self.end_date = end_date
        self.results = []

    @abstractmethod
    def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetches data from the source."""
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Returns the name of the source."""
        pass

    def standardize_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Standardizes raw data into a common format."""
        standardized = []
        for item in raw_data:
            try:
                std_item = self._transform_item(item)
                if std_item:
                    standardized.append(std_item)
            except Exception as e:
                logger.warning(f"Failed to transform item from {self.source_name}: {e}")
        return standardized

    @abstractmethod
    def _transform_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transforms a single raw item into the standard format."""
        pass

class GBIFSource(DataSource):
    """GBIF Data Source implementation."""

    @property
    def source_name(self) -> str:
        return "gbif"

    def fetch_data(self) -> List[Dict[str, Any]]:
        if not gbif_occurrences:
            logger.error("pygbif is not installed. Skipping GBIF.")
            return []

        logger.info(f"Fetching data from GBIF for {self.species_name}...")
        
        # GBIF expects WKT for geometry if using polygon, but here we use bounding box arguments
        # decimalLatitude, decimalLongitude ranges
        # eventDate range
        
        # Note: pygbif search might need pagination handling if results > limit (default 300)
        # We will fetch up to a reasonable limit for this script, e.g., 5000 or loop
        
        limit = 300
        offset = 0
        all_results = []
        
        # Construct geometry string for logging/debugging (not directly used in simple args if we use range)
        # But pygbif search supports 'geometry' as WKT polygon. 
        # For simplicity and robustness with the bounding box provided:
        # decimalLatitude='min,max'
        
        lat_range = f"{self.aoi['min_lat']},{self.aoi['max_lat']}"
        lon_range = f"{self.aoi['min_lon']},{self.aoi['max_lon']}"
        
        # eventDate format: '2016-01-01,2025-12-31' (inclusive range)
        # Ensure dates are YYYY-MM-DD
        # If end_date is 'today', format it.
        
        while True:
            try:
                response = gbif_occurrences.search(
                    scientificName=self.species_name,
                    decimalLatitude=lat_range,
                    decimalLongitude=lon_range,
                    eventDate=f"{self.start_date},{self.end_date}",
                    limit=limit,
                    offset=offset,
                    hasCoordinate=True
                )
                
                results = response.get('results', [])
                if not results:
                    break
                
                all_results.extend(results)
                offset += limit
                
                logger.info(f"Fetched {len(all_results)} records from GBIF so far...")
                
                if response.get('endOfRecords', False):
                    break
                    
                # Safety break to avoid infinite loops or massive downloads in this initial version
                if len(all_results) >= 10000:
                    logger.warning("Reached limit of 10,000 records for GBIF. Stopping.")
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching from GBIF: {e}")
                break

        self.results = all_results
        return self.results

    def _transform_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Required fields: lat, lon, date, source, species
        try:
            return {
                'latitude': item.get('decimalLatitude'),
                'longitude': item.get('decimalLongitude'),
                'date': item.get('eventDate'), # ISO format usually
                'source': 'gbif',
                'species': item.get('scientificName', self.species_name),
                'id': item.get('key'),
                'raw_data': json.dumps(item) # Store raw just in case
            }
        except Exception:
            return None

class iNaturalistSource(DataSource):
    """iNaturalist Data Source implementation."""

    @property
    def source_name(self) -> str:
        return "inaturalist"

    def fetch_data(self) -> List[Dict[str, Any]]:
        if not get_observations:
            logger.error("pyinaturalist is not installed. Skipping iNaturalist.")
            return []

        logger.info(f"Fetching data from iNaturalist for {self.species_name}...")
        
        # iNaturalist params
        # d1, d2 for date range
        # nelat, nelng, swlat, swlng for bounding box
        
        all_results = []
        page = 1
        per_page = 200 # Max is usually 200
        
        while True:
            try:
                response = get_observations(
                    taxon_name=self.species_name,
                    d1=self.start_date,
                    d2=self.end_date,
                    nelat=self.aoi['max_lat'],
                    nelng=self.aoi['max_lon'],
                    swlat=self.aoi['min_lat'],
                    swlng=self.aoi['min_lon'],
                    per_page=per_page,
                    page=page,
                    geoprivacy='open', # Only open data
                    quality_grade='research' # Prefer research grade? Doc didn't specify, but usually good practice. Let's stick to default or 'any' if not specified. Doc says "inaturalist miap project" but let's start with general search.
                    # Actually doc says "gbif and inaturalist miap project". 
                    # If it implies a specific project, we might need project_id. 
                    # But "inaturalist+gbif" implies general sources. I will stick to general search for now.
                )
                
                results = response.get('results', [])
                if not results:
                    break
                
                all_results.extend(results)
                page += 1
                
                logger.info(f"Fetched {len(all_results)} records from iNaturalist so far...")
                
                # Check if we have fetched all
                total_results = response.get('total_results', 0)
                if len(all_results) >= total_results:
                    break
                
                # Safety break
                if len(all_results) >= 10000:
                    logger.warning("Reached limit of 10,000 records for iNaturalist. Stopping.")
                    break

            except Exception as e:
                logger.error(f"Error fetching from iNaturalist: {e}")
                break
                
        self.results = all_results
        return self.results

    def _transform_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            geojson = item.get('geojson')
            if not geojson:
                return None
                
            coords = geojson.get('coordinates', []) # lon, lat
            
            if not coords or len(coords) < 2:
                return None
            
            # Handle potential datetime objects in item for json.dumps
            def json_serial(obj):
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                raise TypeError (f"Type {type(obj)} not serializable")

            return {
                'latitude': coords[1],
                'longitude': coords[0],
                'date': item.get('observed_on'),
                'source': 'inaturalist',
                'species': item.get('taxon', {}).get('name', self.species_name) if item.get('taxon') else self.species_name,
                'id': item.get('id'),
                'raw_data': json.dumps(item, default=json_serial)
            }
        except Exception as e:
            logger.warning(f"Error transforming iNaturalist item {item.get('id')}: {e}")
            return None

def parse_aoi(aoi_path: str) -> Dict[str, float]:
    if not aoi_path:
        return DEFAULT_AOI_BOUNDS
    
    try:
        with open(aoi_path, 'r') as f:
            data = json.load(f)
        
        # Assuming GeoJSON FeatureCollection or Feature
        # We need to extract bounds. This is a simplified bounding box extraction.
        # For a proper implementation, we'd use shapely or similar, but let's keep dependencies low if possible.
        # Or just expect a simple bbox in the file? 
        # The prompt says "path to a geojson".
        # Let's try to find a bbox in the geojson or calculate it from coordinates.
        
        # Very basic bbox calculation
        lats = []
        lons = []
        
        def extract_coords(obj):
            if isinstance(obj, dict):
                if 'coordinates' in obj:
                    coords = obj['coordinates']
                    # Handle different geometry types (Point, Polygon, MultiPolygon)
                    # Flatten recursively
                    def flatten(l):
                        for el in l:
                            if isinstance(el, list) and not isinstance(el[0], (int, float)):
                                flatten(el)
                            elif isinstance(el, list) and len(el) >= 2:
                                lons.append(el[0])
                                lats.append(el[1])
                    flatten(coords)
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        extract_coords(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract_coords(item)

        extract_coords(data)
        
        if not lats or not lons:
            logger.warning("Could not extract coordinates from AOI file. Using default.")
            return DEFAULT_AOI_BOUNDS
            
        return {
            'min_lon': min(lons),
            'max_lon': max(lons),
            'min_lat': min(lats),
            'max_lat': max(lats)
        }
        
    except Exception as e:
        logger.error(f"Error reading AOI file: {e}. Using default.")
        return DEFAULT_AOI_BOUNDS

def main():
    parser = argparse.ArgumentParser(description="Download species observations.")
    parser.add_argument("--species", default="Lantana camara", help="Target species scientific name")
    parser.add_argument("--sources", default="inaturalist,gbif", help="Comma-separated list of sources")
    parser.add_argument("--aoi", help="Path to GeoJSON AOI file")
    parser.add_argument("--output_format", default="json", choices=["csv", "json"], help="Output format")
    parser.add_argument("--output_path", help="Output file path")
    parser.add_argument("--start_date", default="2016-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end_date", default=date.today().isoformat(), help="End date (YYYY-MM-DD)")

    args = parser.parse_args()

    # Determine output path if not provided
    if not args.output_path:
        args.output_path = f"./{args.species.replace(' ', '_')}_observations.{args.output_format}"

    # Parse AOI
    aoi_bounds = parse_aoi(args.aoi)
    logger.info(f"Using AOI bounds: {aoi_bounds}")

    # Initialize sources
    source_map = {
        'gbif': GBIFSource,
        'inaturalist': iNaturalistSource
    }
    
    requested_sources = [s.strip().lower() for s in args.sources.split(',')]
    
    all_data = []
    stats = {}

    for source_name in requested_sources:
        if source_name in source_map:
            source_class = source_map[source_name]
            source_instance = source_class(args.species, aoi_bounds, args.start_date, args.end_date)
            
            try:
                raw_data = source_instance.fetch_data()
                std_data = source_instance.standardize_data(raw_data)
                all_data.extend(std_data)
                stats[source_name] = len(std_data)
            except Exception as e:
                logger.error(f"Failed to process source {source_name}: {e}")
                stats[source_name] = "Failed"
        else:
            logger.warning(f"Unknown source: {source_name}")

    # Write output
    logger.info(f"Writing {len(all_data)} records to {args.output_path}...")
    
    try:
        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError (f"Type {type(obj)} not serializable")

        if args.output_format == 'json':
            with open(args.output_path, 'w') as f:
                json.dump(all_data, f, indent=2, default=json_serial)
        else: # csv
            if all_data:
                keys = all_data[0].keys()
                with open(args.output_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(all_data)
            else:
                logger.warning("No data to write.")
                # Create empty file
                open(args.output_path, 'w').close()
                
    except Exception as e:
        logger.error(f"Error writing output: {e}")

    # Display stats
    print("\n--- Execution Summary ---")
    print(f"Total records fetched: {len(all_data)}")
    for source, count in stats.items():
        print(f"  {source}: {count}")
    
    if os.path.exists(args.output_path):
        size_mb = os.path.getsize(args.output_path) / (1024 * 1024)
        print(f"Output file: {os.path.abspath(args.output_path)} ({size_mb:.2f} MB)")
    else:
        print("Output file not created.")

if __name__ == "__main__":
    main()

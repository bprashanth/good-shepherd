"""
Frappe API Client for Nursery Assistant
Provides a bulletproof wrapper that always includes required headers.
"""
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime


class FrappeClient:
    """
    HTTP client for Frappe API with automatic header management.

    Always includes:
    - Host: nursery.localhost (for multi-tenant routing)
    - Authorization: token-based auth
    - Proper content-type headers

    Usage:
        client = FrappeClient.from_env()
        species = client.get("Species", fields=["name", "accepted_name"])
        batch = client.create("Batch", {"species": "Magnolia", "total_seeds": 100})
    """

    def __init__(self, base_url: str, api_key: str, api_secret: str, site_name: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.api_secret = api_secret
        self.site_name = site_name

        # Note: Using requests library (import at runtime if available)
        try:
            import requests
            self.session = requests.Session()
            self._setup_session()
            self._has_requests = True
        except ImportError:
            # Fallback to curl-based implementation if requests not available
            self._has_requests = False

    def _setup_session(self):
        """Configure session with default headers."""
        self.session.headers.update({
            'Host': self.site_name,
            'Authorization': f'token {self.api_key}:{self.api_secret}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })

    @property
    def headers(self):
        """Get headers dictionary (for compatibility)."""
        if self._has_requests:
            return dict(self.session.headers)
        else:
            # Return headers dict for curl fallback
            return {
                'Host': self.site_name,
                'Authorization': f'token {self.api_key}:{self.api_secret}',
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }

    @classmethod
    def from_env(cls):
        """Create client from environment variables."""
        base_url = os.getenv('FRAPPE_URL', 'http://frappe:8000')
        api_key = os.getenv('FRAPPE_API_KEY')
        api_secret = os.getenv('FRAPPE_API_SECRET')
        site_name = os.getenv('FRAPPE_SITE', 'nursery.localhost')

        if not api_key or not api_secret:
            raise ValueError(
                "FRAPPE_API_KEY and FRAPPE_API_SECRET must be set in environment"
            )

        return cls(base_url, api_key, api_secret, site_name)

    def get(self, doctype: str,
            name: Optional[str] = None,
            filters: Optional[List] = None,
            fields: Optional[List[str]] = None,
            limit: Optional[int] = None) -> Any:
        """
        Get documents from Frappe.

        Args:
            doctype: DocType name (e.g., "Species", "Batch")
            name: Specific document name (optional)
            filters: Frappe filter syntax (optional)
            fields: List of fields to return (optional)
            limit: Max number of results (optional)

        Returns:
            List of documents or single document if name provided

        Example:
            # Get all species
            species = client.get("Species")

            # Get specific batch
            batch = client.get("Batch", name="BATCH-001")

            # Get with filters
            batches = client.get("Batch",
                                filters=[["stage", "=", "germination"]],
                                fields=["name", "species", "total_seeds"])
        """
        if name:
            # Get single document
            url = f"{self.base_url}/api/resource/{doctype}/{name}"
            params = {}
        else:
            # Get list of documents
            url = f"{self.base_url}/api/resource/{doctype}"
            params = {}
            if filters:
                params['filters'] = json.dumps(filters)
            if fields:
                params['fields'] = json.dumps(fields)
            if limit:
                params['limit'] = limit

        if self._has_requests:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get('data')
        else:
            # Fallback: use curl (for environments without requests)
            return self._curl_get(url, params)

    def create(self, doctype: str, data: Dict[str, Any]) -> Dict:
        """
        Create a new document.

        Args:
            doctype: DocType name
            data: Document data

        Returns:
            Created document

        Example:
            batch = client.create("Batch", {
                "species": "Magnolia champaca",
                "total_seeds": 100,
                "date_sown": "2024-01-15",
                "section": "B",
                "bed": "B1"
            })
        """
        url = f"{self.base_url}/api/resource/{doctype}"

        if self._has_requests:
            resp = self.session.post(url, json=data, timeout=30)

            # Handle duplicate (409 Conflict)
            if resp.status_code == 409:
                return None

            resp.raise_for_status()
            return resp.json().get('data')
        else:
            return self._curl_post(url, data)

    def update(self, doctype: str, name: str, data: Dict[str, Any]) -> Dict:
        """
        Update an existing document.

        Args:
            doctype: DocType name
            name: Document name
            data: Fields to update

        Returns:
            Updated document

        Example:
            client.update("Batch", "BATCH-001", {"stage": "germination"})
        """
        url = f"{self.base_url}/api/resource/{doctype}/{name}"

        if self._has_requests:
            resp = self.session.put(url, json=data, timeout=30)
            resp.raise_for_status()
            return resp.json().get('data')
        else:
            return self._curl_put(url, data)

    def ping(self) -> bool:
        """
        Test API connectivity.

        Returns:
            True if API is reachable
        """
        try:
            url = f"{self.base_url}/api/method/ping"
            if self._has_requests:
                resp = self.session.get(url, timeout=5)
                return resp.status_code == 200 and resp.json().get('message') == 'pong'
            else:
                result = self._curl_get(url, {})
                return result.get('message') == 'pong'
        except Exception:
            return False

    def get_doctype_meta(self, doctype: str) -> Dict[str, Any]:
        """
        Get DocType metadata (schema) from Frappe.

        This returns the full DocType definition including:
        - All fields and their types
        - Child tables
        - Required fields
        - Options/choices

        Args:
            doctype: DocType name (e.g., "Species", "Batch")

        Returns:
            Dictionary with DocType metadata

        Example:
            meta = client.get_doctype_meta("Species")
            for field in meta['fields']:
                print(f"{field['fieldname']}: {field['fieldtype']} (required: {field.get('reqd', 0)})")
        """
        return self.get("DocType", name=doctype)

    # Curl fallback methods (if requests library not available)
    def _curl_get(self, url: str, params: Dict) -> Any:
        """Fallback GET using curl."""
        import subprocess
        param_str = '&'.join(f"{k}={v}" for k, v in params.items())
        full_url = f"{url}?{param_str}" if param_str else url

        cmd = [
            'curl', '-s',
            '-H', f'Host: {self.site_name}',
            '-H', f'Authorization: token {self.api_key}:{self.api_secret}',
            '-H', 'Accept: application/json',
            full_url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)

    def _curl_post(self, url: str, data: Dict) -> Any:
        """Fallback POST using curl."""
        import subprocess
        cmd = [
            'curl', '-s', '-X', 'POST',
            '-H', f'Host: {self.site_name}',
            '-H', f'Authorization: token {self.api_key}:{self.api_secret}',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps(data),
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)

    def _curl_put(self, url: str, data: Dict) -> Any:
        """Fallback PUT using curl."""
        import subprocess
        cmd = [
            'curl', '-s', '-X', 'PUT',
            '-H', f'Host: {self.site_name}',
            '-H', f'Authorization: token {self.api_key}:{self.api_secret}',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps(data),
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)


# Convenience helper functions
def get_species_by_name(client: FrappeClient, name: str) -> Optional[Dict]:
    """Find species by scientific name."""
    results = client.get("Species",
                        filters=[["accepted_name", "=", name]],
                        fields=["name", "accepted_name", "iucn_status"])
    return results[0] if results else None


def get_batches_by_stage(client: FrappeClient, stage: str) -> List[Dict]:
    """Get all batches in a specific stage."""
    return client.get("Batch",
                     filters=[["stage", "=", stage]],
                     fields=["name", "species", "date_sown", "total_seeds",
                            "section", "bed"])


def create_germination_event(client: FrappeClient,
                             batch_name: str,
                             quantity: int,
                             event_date: Optional[str] = None) -> Dict:
    """Create a germination event for a batch."""
    if not event_date:
        event_date = datetime.now().strftime("%Y-%m-%d")

    event = client.create("Nursery Event", {
        "batch": batch_name,
        "event_type": "germination",
        "event_date": event_date,
        "quantity": quantity,
    })

    # Update batch stage
    client.update("Batch", batch_name, {"stage": "germination"})

    return event

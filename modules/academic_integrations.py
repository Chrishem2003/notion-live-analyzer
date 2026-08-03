
"""
Academic Integrations  Zotero, Mendeley, Grant Finder, LaTeX Exporter.
"""
import os
import json
import time
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
import streamlit as st
import requests

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ZOTERO INTEGRATION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ZoteroClient:
    """Zotero reference manager integration."""
    
    def __init__(self, api_key: str = None, user_id: str = None):
        self.api_key = api_key or os.environ.get("ZOTERO_API_KEY", "")
        self.user_id = user_id or os.environ.get("ZOTERO_USER_ID", "")
        self.base_url = "https://api.zotero.org"
    
    def _headers(self) -> dict:
        return {
            "Zotero-API-Key": self.api_key,
            "Zotero-API-Version": "3",
        }
    
    def get_collections(self) -> List[Dict]:
        """Get all Zotero collections."""
        if not self.api_key or not self.user_id:
            return []
        
        try:
            response = requests.get(
                f"{self.base_url}/users/{self.user_id}/collections",
                headers=self._headers(),
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []
    
    def get_items(self, collection_id: str = None, limit: int = 50) -> List[Dict]:
        """Get items from Zotero library."""
        if not self.api_key:
            return []
        
        url = f"{self.base_url}/users/{self.user_id}/items"
        params = {"limit": limit, "format": "json"}
        
        if collection_id:
            url = f"/collections/{collection_id}"
        
        try:
            response = requests.get(url, headers=self._headers(), params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []
    
    def create_item(self, item_data: Dict) -> bool:
        """Add item to Zotero library."""
        if not self.api_key:
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/users/{self.user_id}/items",
                headers=self._headers(),
                json=[item_data],
                timeout=10,
            )
            return response.status_code in (200, 201)
        except Exception:
            return False
    
    def sync_from_app(self, papers: List[Dict]) -> int:
        """Sync papers from app to Zotero."""
        synced = 0
        for paper in papers:
            item = {
                "itemType": "journalArticle",
                "title": paper.get("title", ""),
                "creators": [{"creatorType": "author", "firstName": "", "lastName": a} 
                            for a in paper.get("authors", [])],
                "date": paper.get("year", ""),
                "url": paper.get("url", ""),
                "abstractNote": paper.get("abstract", ""),
            }
            if self.create_item(item):
                synced = 1
        return synced

@st.cache_resource(ttl=3600)
def get_zotero_client() -> Optional[ZoteroClient]:
    """Get cached Zotero client."""
    return ZoteroClient()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# MENDELEY INTEGRATION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class MendeleyClient:
    """Mendeley reference manager integration."""
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or os.environ.get("MENDELEY_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("MENDELEY_CLIENT_SECRET", "")
        self.access_token = None
        self.base_url = "https://api.mendeley.com"
    
    def authenticate(self) -> bool:
        """Authenticate with Mendeley OAuth."""
        if not self.client_id:
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10,
            )
            if response.status_code == 200:
                self.access_token = response.json().get("access_token")
                return True
        except Exception:
            pass
        return False
    
    def get_documents(self, limit: int = 50) -> List[Dict]:
        """Get Mendeley documents."""
        if not self.access_token:
            return []
        
        try:
            response = requests.get(
                f"{self.base_url}/documents",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params={"limit": limit},
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []

@st.cache_resource(ttl=3600)
def get_mendeley_client() -> Optional[MendeleyClient]:
    """Get cached Mendeley client."""
    return MendeleyClient()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# GRANT FINDER
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class GrantFinder:
    """Automated grant eligibility finder."""
    
    # Sample grant databases (in production, use real APIs)
    GRANT_DATABASES = [
        {
            "name": "NIH Research Grants",
            "url": "https://grants.nih.gov",
            "focus": ["health", "medicine", "biology"],
            "max_amount": 5000000,
            "eligibility": ["academic", "nonprofit"],
        },
        {
            "name": "NSF Grants",
            "url": "https://nsf.gov",
            "focus": ["science", "engineering", "technology"],
            "max_amount": 3000000,
            "eligibility": ["academic"],
        },
        {
            "name": "Wellcome Trust",
            "url": "https://wellcome.org",
            "focus": ["health", "biomedical"],
            "max_amount": 4000000,
            "eligibility": ["academic", "nonprofit"],
        },
        {
            "name": "Bill & Melinda Gates Foundation",
            "url": "https://gatesfoundation.org",
            "focus": ["health", "global development"],
            "max_amount": 10000000,
            "eligibility": ["academic", "nonprofit"],
        },
        {
            "name": "Ford Foundation",
            "url": "https://fordfoundation.org",
            "focus": ["social justice", "education"],
            "max_amount": 500000,
            "eligibility": ["academic", "nonprofit"],
        },
        {
            "name": "UNESCO Grants",
            "url": "https://unesco.org",
            "focus": ["education", "science", "culture"],
            "max_amount": 1000000,
            "eligibility": ["academic", "government"],
        },
        {
            "name": "European Research Council",
            "url": "https://erc.europa.eu",
            "focus": ["science", "innovation"],
            "max_amount": 2000000,
            "eligibility": ["academic"],
        },
        {
            "name": "African Development Bank",
            "url": "https://afdb.org",
            "focus": ["development", "research"],
            "max_amount": 500000,
            "eligibility": ["academic", "government", "nonprofit"],
        },
    ]
    
    def find_matching_grants(
        self,
        topic: str,
        research_area: str = "",
        amount_needed: int = 0,
    ) -> List[Dict]:
        """Find grants matching research topic."""
        topic_lower = topic.lower()
        results = []
        
        for grant in self.GRANT_DATABASES:
            # Check topic relevance
            relevance_score = 0
            for focus in grant["focus"]:
                if focus in topic_lower:
                    relevance_score = 1
            
            if relevance_score == 0:
                continue
            
            # Check amount eligibility
            if amount_needed > 0 and amount_needed > grant["max_amount"]:
                continue
            
            results.append({
                **grant,
                "relevance_score": relevance_score,
                "deadline": "Rolling" if "rolling" in grant.get("deadline", "") else "Check website",
            })
        
        return sorted(results, key=lambda x: x["relevance_score"], reverse=True)
    

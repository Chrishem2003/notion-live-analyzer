
import requests
import xml.etree.ElementTree as ET
from modules.api_safeguards import safe_api_request

def fetch_ncbi_gene_summary(term: str, api_key: str = None) -> dict:
    """Searches NCBI Gene database and retrieves summary information."""
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "gene",
        "term": term,
        "retmode": "json",
        "retmax": 1
    }
    if api_key:
        params["api_key"] = api_key

    res = safe_api_request("GET", search_url, params=params, service_type="pubmed")
    data = res.json()
    id_list = data.get("esearchresult", {}).get("idlist", [])

    if not id_list:
        return {"error": f"No NCBI Gene entry found for term: {term}"}

    gene_id = id_list[0]
    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    sum_params = {
        "db": "gene",
        "id": gene_id,
        "retmode": "json"
    }
    if api_key:
        sum_params["api_key"] = api_key

    sum_res = safe_api_request("GET", summary_url, params=sum_params, service_type="pubmed")
    sum_data = sum_res.json().get("result", {}).get(gene_id, {})

    return {
        "gene_id": gene_id,
        "name": sum_data.get("name", "N/A"),
        "description": sum_data.get("description", "N/A"),
        "organism": sum_data.get("organism", {}).get("scientificname", "N/A"),
        "chromosome": sum_data.get("chromosome", "N/A")
    }

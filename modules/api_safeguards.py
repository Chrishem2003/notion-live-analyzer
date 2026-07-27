import time
import requests
import logging
from typing import Dict, Any, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("APISafeguards")

class RateLimitException(Exception):
    pass

class SimpleRateLimiter:
    def __init__(self, max_per_second: float):
        self.min_interval = 1.0 / max_per_second
        self.last_call = 0.0

    def wait(self):
        elapsed = time.time() - self.last_call
        left_to_wait = self.min_interval - elapsed
        if left_to_wait > 0:
            time.sleep(left_to_wait)
        self.last_call = time.time()

pubmed_limiter = SimpleRateLimiter(max_per_second=2.5)
notion_limiter = SimpleRateLimiter(max_per_second=2.5)

def set_pubmed_key_mode(has_api_key: bool):
    global pubmed_limiter
    rate = 9.0 if has_api_key else 2.5
    pubmed_limiter = SimpleRateLimiter(max_per_second=rate)

@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(min=1, max=16),
    retry=retry_if_exception_type((RateLimitException, requests.exceptions.ConnectionError, requests.exceptions.Timeout))
)
def safe_api_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    timeout: int = 10,
    service_type: str = "generic"
) -> requests.Response:
    if service_type == "pubmed":
        pubmed_limiter.wait()
    elif service_type == "notion":
        notion_limiter.wait()

    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        params=params,
        json=json_data,
        timeout=timeout
    )

    if response.status_code == 429 or response.status_code in [502, 503, 504]:
        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            time.sleep(int(retry_after))
        raise RateLimitException(f"Throttled by {service_type} (HTTP {response.status_code}). Retrying...")

    response.raise_for_status()
    return response

from __future__ import annotations

from sovereign_intelligence.models import AIRequest, AIResponse
from sovereign_intelligence.providers.failover import ProviderFailover
from sovereign_intelligence.providers.routing_models import ProviderCandidate


class FakeFailingProvider:
    def __init__(self):
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        raise RuntimeError("primary provider intentionally failed")


class FakeSuccessfulProvider:
    def __init__(self):
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return AIResponse(
            text="Fallback provider succeeded.",
            provider=request.provider or "",
            model=request.model or "",
        )


def test_primary_failure_routes_to_fallback():
    primary = FakeFailingProvider()
    fallback = FakeSuccessfulProvider()

    providers = {
        "primary": primary,
        "fallback": fallback,
    }

    failover = ProviderFailover(
        providers=providers,
        candidates=[
            ProviderCandidate(
                name="primary",
                model="primary-model",
                priority=10,
            ),
            ProviderCandidate(
                name="fallback",
                model="fallback-model",
                priority=20,
            ),
        ],
    )

    request = AIRequest(
        prompt="Test provider failover.",
        model="primary-model",
        provider="primary",
    )

    result = failover.execute(
        request,
        preferred_provider="primary",
        preferred_model="primary-model",
    )

    assert len(result.attempts) == 2

    assert result.attempts[0].provider == "primary"
    assert result.attempts[0].model == "primary-model"
    assert result.attempts[0].success is False

    assert result.attempts[1].provider == "fallback"
    assert result.attempts[1].model == "fallback-model"
    assert result.attempts[1].success is True

    assert result.attempts[1].response is not None
    assert result.attempts[1].response.text == "Fallback provider succeeded."

    assert len(primary.requests) == 1
    assert primary.requests[0].provider == "primary"
    assert primary.requests[0].model == "primary-model"

    assert len(fallback.requests) == 1
    assert fallback.requests[0].provider == "fallback"
    assert fallback.requests[0].model == "fallback-model"


def test_failover_preserves_original_request():
    primary = FakeFailingProvider()
    fallback = FakeSuccessfulProvider()

    request = AIRequest(
        prompt="Preserve this request.",
        model="primary-model",
        provider="primary",
    )

    original_provider = request.provider
    original_model = request.model

    failover = ProviderFailover(
        providers={
            "primary": primary,
            "fallback": fallback,
        },
        candidates=[
            ProviderCandidate(
                name="primary",
                model="primary-model",
                priority=10,
            ),
            ProviderCandidate(
                name="fallback",
                model="fallback-model",
                priority=20,
            ),
        ],
    )

    failover.execute(
        request,
        preferred_provider="primary",
        preferred_model="primary-model",
    )

    assert request.provider == original_provider
    assert request.model == original_model
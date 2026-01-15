# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Synth-Mind LLM Integration for NatLangChain.

Provides shared LLM routing and model management for RRA agents,
integrating with the NatLangChain synth-mind system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, AsyncIterator
from pathlib import Path
import json
import secrets
import asyncio
from abc import ABC, abstractmethod


class ModelProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    CUSTOM = "custom"


class ModelCapability(Enum):
    """Model capabilities."""

    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    CODE = "code"
    REASONING = "reasoning"
    FUNCTION_CALLING = "function_calling"


class RequestPriority(Enum):
    """Priority levels for LLM requests."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ModelConfig:
    """Configuration for an LLM model."""

    model_id: str
    provider: ModelProvider
    model_name: str
    capabilities: List[ModelCapability]
    max_tokens: int = 4096
    temperature: float = 0.7
    cost_per_1k_tokens: float = 0.0
    rate_limit_rpm: int = 60  # Requests per minute
    enabled: bool = True
    priority: int = 1  # Higher = preferred

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "provider": self.provider.value,
            "model_name": self.model_name,
            "capabilities": [c.value for c in self.capabilities],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "cost_per_1k_tokens": self.cost_per_1k_tokens,
            "rate_limit_rpm": self.rate_limit_rpm,
            "enabled": self.enabled,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        return cls(
            model_id=data["model_id"],
            provider=ModelProvider(data["provider"]),
            model_name=data["model_name"],
            capabilities=[ModelCapability(c) for c in data["capabilities"]],
            max_tokens=data.get("max_tokens", 4096),
            temperature=data.get("temperature", 0.7),
            cost_per_1k_tokens=data.get("cost_per_1k_tokens", 0.0),
            rate_limit_rpm=data.get("rate_limit_rpm", 60),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 1),
        )


@dataclass
class LLMRequest:
    """An LLM inference request."""

    request_id: str
    model_id: Optional[str]  # None = auto-select
    messages: List[Dict[str, str]]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    priority: RequestPriority = RequestPriority.NORMAL
    required_capabilities: List[ModelCapability] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "messages": self.messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "priority": self.priority.value,
            "required_capabilities": [c.value for c in self.required_capabilities],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class LLMResponse:
    """Response from LLM inference."""

    request_id: str
    model_id: str
    content: str
    tokens_used: int
    finish_reason: str
    latency_ms: float
    cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "model_id": self.model_id,
            "content": self.content,
            "tokens_used": self.tokens_used,
            "finish_reason": self.finish_reason,
            "latency_ms": self.latency_ms,
            "cost": self.cost,
            "metadata": self.metadata,
        }


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def complete(
        self, model_name: str, messages: List[Dict[str, str]], max_tokens: int, temperature: float
    ) -> tuple[str, int, str]:
        """
        Complete a chat request.

        Returns:
            Tuple of (content, tokens_used, finish_reason)
        """

    @abstractmethod
    async def stream(
        self, model_name: str, messages: List[Dict[str, str]], max_tokens: int, temperature: float
    ) -> AsyncIterator[str]:
        """Stream a chat response."""


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    async def complete(
        self, model_name: str, messages: List[Dict[str, str]], max_tokens: int, temperature: float
    ) -> tuple[str, int, str]:
        # Simulate response
        last_message = messages[-1]["content"] if messages else ""
        response = f"Mock response to: {last_message[:50]}..."
        return response, len(response.split()), "stop"

    async def stream(
        self, model_name: str, messages: List[Dict[str, str]], max_tokens: int, temperature: float
    ) -> AsyncIterator[str]:
        response = "This is a streaming mock response."
        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.05)


@dataclass
class RateLimitState:
    """Tracks rate limit state for a model."""

    model_id: str
    requests_this_minute: int = 0
    minute_start: datetime = field(default_factory=datetime.now)
    total_requests: int = 0
    total_tokens: int = 0

    def check_and_increment(self, limit: int) -> bool:
        """Check if under rate limit and increment counter."""
        now = datetime.now()

        # Reset if new minute
        if (now - self.minute_start).total_seconds() >= 60:
            self.requests_this_minute = 0
            self.minute_start = now

        if self.requests_this_minute >= limit:
            return False

        self.requests_this_minute += 1
        self.total_requests += 1
        return True


class SynthMindRouter:
    """
    LLM Router for synth-mind integration.

    Handles model selection, load balancing, rate limiting,
    and request routing for RRA agents.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/synth_mind")
        self.models: Dict[str, ModelConfig] = {}
        self.providers: Dict[ModelProvider, LLMProvider] = {}
        self.rate_limits: Dict[str, RateLimitState] = {}
        self.request_history: List[Dict[str, Any]] = []

        # Register mock provider by default
        self.providers[ModelProvider.LOCAL] = MockLLMProvider()

        if data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()
        else:
            self._register_default_models()

    def _generate_id(self, prefix: str = "") -> str:
        return f"{prefix}{secrets.token_hex(8)}"

    def _register_default_models(self) -> None:
        """Register default model configurations."""
        # GPT-4 style model
        self.register_model(
            ModelConfig(
                model_id="gpt4",
                provider=ModelProvider.OPENAI,
                model_name="gpt-4",
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE,
                    ModelCapability.REASONING,
                    ModelCapability.FUNCTION_CALLING,
                ],
                max_tokens=8192,
                cost_per_1k_tokens=0.03,
                priority=3,
            )
        )

        # Claude style model
        self.register_model(
            ModelConfig(
                model_id="claude",
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-3-opus",
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.CODE,
                    ModelCapability.REASONING,
                ],
                max_tokens=4096,
                cost_per_1k_tokens=0.015,
                priority=2,
            )
        )

        # Local/mock model
        self.register_model(
            ModelConfig(
                model_id="local",
                provider=ModelProvider.LOCAL,
                model_name="mock-model",
                capabilities=[
                    ModelCapability.CHAT,
                    ModelCapability.COMPLETION,
                ],
                max_tokens=2048,
                cost_per_1k_tokens=0.0,
                priority=1,
            )
        )

    # =========================================================================
    # Model Management
    # =========================================================================

    def register_model(self, config: ModelConfig) -> ModelConfig:
        """Register a model configuration."""
        self.models[config.model_id] = config
        self.rate_limits[config.model_id] = RateLimitState(model_id=config.model_id)
        self._save_state()
        return config

    def register_provider(self, provider_type: ModelProvider, provider: LLMProvider) -> None:
        """Register an LLM provider implementation."""
        self.providers[provider_type] = provider

    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        return self.models.get(model_id)

    def list_models(
        self, enabled_only: bool = True, capability: Optional[ModelCapability] = None
    ) -> List[ModelConfig]:
        """List available models."""
        models = list(self.models.values())

        if enabled_only:
            models = [m for m in models if m.enabled]

        if capability:
            models = [m for m in models if capability in m.capabilities]

        return sorted(models, key=lambda m: -m.priority)

    def select_model(
        self,
        required_capabilities: List[ModelCapability],
        preferred_model: Optional[str] = None,
        max_cost: Optional[float] = None,
    ) -> Optional[ModelConfig]:
        """
        Select the best model for a request.

        Considers capabilities, cost, rate limits, and priority.
        """
        # If preferred model specified and valid, use it
        if preferred_model:
            model = self.models.get(preferred_model)
            if model and model.enabled:
                # Check capabilities
                if all(c in model.capabilities for c in required_capabilities):
                    return model

        # Find all matching models
        candidates = []
        for model in self.models.values():
            if not model.enabled:
                continue

            # Check capabilities
            if not all(c in model.capabilities for c in required_capabilities):
                continue

            # Check cost
            if max_cost is not None and model.cost_per_1k_tokens > max_cost:
                continue

            # Check rate limit
            rate_state = self.rate_limits.get(model.model_id)
            if rate_state and not rate_state.check_and_increment(model.rate_limit_rpm):
                continue

            candidates.append(model)

        if not candidates:
            return None

        # Sort by priority and return best
        candidates.sort(key=lambda m: -m.priority)
        return candidates[0]

    # =========================================================================
    # Request Handling
    # =========================================================================

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        required_capabilities: Optional[List[ModelCapability]] = None,
        priority: RequestPriority = RequestPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """
        Complete a chat request.

        Auto-selects model if not specified.
        """
        request_id = self._generate_id("req_")
        start_time = datetime.now()

        # Select model
        required_caps = required_capabilities or [ModelCapability.CHAT]
        model = self.select_model(required_caps, model_id)

        if not model:
            raise ValueError("No suitable model available")

        # Get provider
        provider = self.providers.get(model.provider)
        if not provider:
            raise ValueError(f"No provider registered for: {model.provider.value}")

        # Execute request
        content, tokens, finish_reason = await provider.complete(
            model_name=model.model_name,
            messages=messages,
            max_tokens=max_tokens or model.max_tokens,
            temperature=temperature if temperature is not None else model.temperature,
        )

        # Calculate metrics
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000
        cost = (tokens / 1000) * model.cost_per_1k_tokens

        # Update rate limit state
        if model.model_id in self.rate_limits:
            self.rate_limits[model.model_id].total_tokens += tokens

        response = LLMResponse(
            request_id=request_id,
            model_id=model.model_id,
            content=content,
            tokens_used=tokens,
            finish_reason=finish_reason,
            latency_ms=latency_ms,
            cost=cost,
            metadata=metadata or {},
        )

        # Log request
        self._log_request(request_id, model.model_id, tokens, latency_ms, cost)

        return response

    async def stream(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[str]:
        """Stream a chat response."""
        required_caps = [ModelCapability.CHAT]
        model = self.select_model(required_caps, model_id)

        if not model:
            raise ValueError("No suitable model available")

        provider = self.providers.get(model.provider)
        if not provider:
            raise ValueError(f"No provider registered for: {model.provider.value}")

        async for chunk in provider.stream(
            model_name=model.model_name,
            messages=messages,
            max_tokens=max_tokens or model.max_tokens,
            temperature=temperature if temperature is not None else model.temperature,
        ):
            yield chunk

    def _log_request(
        self, request_id: str, model_id: str, tokens: int, latency_ms: float, cost: float
    ) -> None:
        """Log a request for analytics."""
        self.request_history.append(
            {
                "request_id": request_id,
                "model_id": model_id,
                "tokens": tokens,
                "latency_ms": latency_ms,
                "cost": cost,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Keep last 1000 requests
        if len(self.request_history) > 1000:
            self.request_history = self.request_history[-1000:]

    # =========================================================================
    # Negotiation-Specific Methods
    # =========================================================================

    async def generate_negotiation_response(
        self,
        context: str,
        buyer_message: str,
        agent_personality: str = "professional",
        price_range: Optional[tuple[float, float]] = None,
    ) -> str:
        """Generate a negotiation response for RRA agents."""
        system_prompt = f"""You are a license negotiation agent with a {agent_personality} personality.
Your goal is to negotiate fair license terms for software repositories.
{f'The acceptable price range is {price_range[0]} to {price_range[1]} ETH.' if price_range else ''}

Context about the repository:
{context}

Respond professionally and aim to reach a mutually beneficial agreement."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": buyer_message},
        ]

        response = await self.complete(
            messages=messages,
            required_capabilities=[ModelCapability.CHAT, ModelCapability.REASONING],
            priority=RequestPriority.HIGH,
        )

        return response.content

    async def analyze_code_value(
        self, code_summary: str, metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze code to determine licensing value."""
        prompt = f"""Analyze this code repository and estimate its licensing value.

Code Summary:
{code_summary}

Metrics:
- Lines of code: {metrics.get('loc', 'unknown')}
- Stars: {metrics.get('stars', 0)}
- Forks: {metrics.get('forks', 0)}
- Languages: {metrics.get('languages', [])}

Provide:
1. Estimated value range (in ETH)
2. Key value factors
3. Recommended license tiers
4. Risk assessment

Format as JSON."""

        messages = [{"role": "user", "content": prompt}]

        response = await self.complete(
            messages=messages,
            required_capabilities=[ModelCapability.CODE, ModelCapability.REASONING],
        )

        # Parse JSON response
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"raw_response": response.content}

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get LLM usage statistics."""
        recent = [
            r
            for r in self.request_history
            if datetime.fromisoformat(r["timestamp"]) > datetime.now() - timedelta(hours=24)
        ]

        total_cost = sum(r["cost"] for r in recent)
        total_tokens = sum(r["tokens"] for r in recent)
        avg_latency = sum(r["latency_ms"] for r in recent) / len(recent) if recent else 0

        by_model = {}
        for r in recent:
            model_id = r["model_id"]
            if model_id not in by_model:
                by_model[model_id] = {"requests": 0, "tokens": 0, "cost": 0}
            by_model[model_id]["requests"] += 1
            by_model[model_id]["tokens"] += r["tokens"]
            by_model[model_id]["cost"] += r["cost"]

        return {
            "requests_24h": len(recent),
            "total_tokens_24h": total_tokens,
            "total_cost_24h": total_cost,
            "avg_latency_ms": avg_latency,
            "by_model": by_model,
            "registered_models": len(self.models),
            "enabled_models": len([m for m in self.models.values() if m.enabled]),
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_state(self) -> None:
        if not self.data_dir:
            return

        # Ensure directory exists before writing
        self.data_dir.mkdir(parents=True, exist_ok=True)

        state = {
            "models": {mid: m.to_dict() for mid, m in self.models.items()},
        }

        with open(self.data_dir / "synth_mind_state.json", "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> None:
        state_file = self.data_dir / "synth_mind_state.json"
        if not state_file.exists():
            self._register_default_models()
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            self.models = {
                mid: ModelConfig.from_dict(m) for mid, m in state.get("models", {}).items()
            }

            # Initialize rate limits
            for model_id in self.models:
                self.rate_limits[model_id] = RateLimitState(model_id=model_id)
        except (json.JSONDecodeError, KeyError):
            self._register_default_models()


def create_synth_mind_router(data_dir: Optional[str] = None) -> SynthMindRouter:
    """Factory function to create a synth-mind router."""
    path = Path(data_dir) if data_dir else None
    return SynthMindRouter(data_dir=path)

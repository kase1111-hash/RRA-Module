# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Agent-OS Runtime Integration for NatLangChain.

Provides distributed agent deployment and lifecycle management,
integrating with the NatLangChain Agent-OS runtime system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import json
import secrets
import asyncio
from abc import ABC, abstractmethod


class AgentStatus(Enum):
    """Status of an agent instance."""

    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    TERMINATED = "terminated"


class AgentType(Enum):
    """Types of RRA agents."""

    NEGOTIATOR = "negotiator"
    BUYER = "buyer"
    ANALYZER = "analyzer"
    MONITOR = "monitor"
    WEBHOOK = "webhook"


class ResourceTier(Enum):
    """Resource allocation tiers."""

    MINIMAL = "minimal"  # 128MB RAM, 0.1 CPU
    STANDARD = "standard"  # 512MB RAM, 0.5 CPU
    ENHANCED = "enhanced"  # 1GB RAM, 1 CPU
    PREMIUM = "premium"  # 2GB RAM, 2 CPU


@dataclass
class ResourceAllocation:
    """Resource allocation for an agent."""

    memory_mb: int = 512
    cpu_cores: float = 0.5
    storage_mb: int = 100
    network_bandwidth_mbps: int = 10

    @classmethod
    def from_tier(cls, tier: ResourceTier) -> "ResourceAllocation":
        """Create allocation from tier."""
        tiers = {
            ResourceTier.MINIMAL: cls(128, 0.1, 50, 5),
            ResourceTier.STANDARD: cls(512, 0.5, 100, 10),
            ResourceTier.ENHANCED: cls(1024, 1.0, 500, 50),
            ResourceTier.PREMIUM: cls(2048, 2.0, 1000, 100),
        }
        return tiers.get(tier, tiers[ResourceTier.STANDARD])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_mb": self.memory_mb,
            "cpu_cores": self.cpu_cores,
            "storage_mb": self.storage_mb,
            "network_bandwidth_mbps": self.network_bandwidth_mbps,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceAllocation":
        return cls(
            memory_mb=data.get("memory_mb", 512),
            cpu_cores=data.get("cpu_cores", 0.5),
            storage_mb=data.get("storage_mb", 100),
            network_bandwidth_mbps=data.get("network_bandwidth_mbps", 10),
        )


@dataclass
class AgentConfig:
    """Configuration for deploying an agent."""

    agent_type: AgentType
    name: str
    description: str
    repo_id: Optional[str] = None  # Associated repository
    knowledge_base_path: Optional[str] = None
    market_config_path: Optional[str] = None
    resources: ResourceAllocation = field(default_factory=ResourceAllocation)
    environment: Dict[str, str] = field(default_factory=dict)
    auto_restart: bool = True
    max_restarts: int = 3
    health_check_interval_seconds: int = 60

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type.value,
            "name": self.name,
            "description": self.description,
            "repo_id": self.repo_id,
            "knowledge_base_path": self.knowledge_base_path,
            "market_config_path": self.market_config_path,
            "resources": self.resources.to_dict(),
            "environment": self.environment,
            "auto_restart": self.auto_restart,
            "max_restarts": self.max_restarts,
            "health_check_interval_seconds": self.health_check_interval_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        return cls(
            agent_type=AgentType(data["agent_type"]),
            name=data["name"],
            description=data.get("description", ""),
            repo_id=data.get("repo_id"),
            knowledge_base_path=data.get("knowledge_base_path"),
            market_config_path=data.get("market_config_path"),
            resources=ResourceAllocation.from_dict(data.get("resources", {})),
            environment=data.get("environment", {}),
            auto_restart=data.get("auto_restart", True),
            max_restarts=data.get("max_restarts", 3),
            health_check_interval_seconds=data.get("health_check_interval_seconds", 60),
        )


@dataclass
class AgentInstance:
    """A running agent instance."""

    instance_id: str
    config: AgentConfig
    status: AgentStatus
    node_id: str  # Which node it's running on
    created_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    restart_count: int = 0
    last_health_check: Optional[datetime] = None
    health_status: str = "unknown"
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def uptime_seconds(self) -> float:
        if not self.started_at or self.status != AgentStatus.RUNNING:
            return 0.0
        return (datetime.now() - self.started_at).total_seconds()

    @property
    def is_healthy(self) -> bool:
        if self.status != AgentStatus.RUNNING:
            return False
        if self.health_status != "healthy":
            return False
        if self.last_health_check:
            age = (datetime.now() - self.last_health_check).total_seconds()
            if age > self.config.health_check_interval_seconds * 2:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "config": self.config.to_dict(),
            "status": self.status.value,
            "node_id": self.node_id,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "restart_count": self.restart_count,
            "last_health_check": (
                self.last_health_check.isoformat() if self.last_health_check else None
            ),
            "health_status": self.health_status,
            "error_message": self.error_message,
            "metrics": self.metrics,
            "uptime_seconds": self.uptime_seconds,
            "is_healthy": self.is_healthy,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentInstance":
        instance = cls(
            instance_id=data["instance_id"],
            config=AgentConfig.from_dict(data["config"]),
            status=AgentStatus(data["status"]),
            node_id=data["node_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            restart_count=data.get("restart_count", 0),
            health_status=data.get("health_status", "unknown"),
            error_message=data.get("error_message"),
            metrics=data.get("metrics", {}),
        )
        if data.get("started_at"):
            instance.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("stopped_at"):
            instance.stopped_at = datetime.fromisoformat(data["stopped_at"])
        if data.get("last_health_check"):
            instance.last_health_check = datetime.fromisoformat(data["last_health_check"])
        return instance


@dataclass
class RuntimeNode:
    """A node in the Agent-OS cluster."""

    node_id: str
    name: str
    host: str
    port: int
    status: str = "active"
    capacity: ResourceAllocation = field(
        default_factory=lambda: ResourceAllocation(8192, 8.0, 100000, 1000)
    )
    allocated: ResourceAllocation = field(default_factory=ResourceAllocation)
    agent_count: int = 0
    region: str = "default"
    tags: List[str] = field(default_factory=list)
    last_heartbeat: Optional[datetime] = None

    @property
    def available_memory(self) -> int:
        return self.capacity.memory_mb - self.allocated.memory_mb

    @property
    def available_cpu(self) -> float:
        return self.capacity.cpu_cores - self.allocated.cpu_cores

    @property
    def utilization(self) -> float:
        mem_util = (
            self.allocated.memory_mb / self.capacity.memory_mb if self.capacity.memory_mb > 0 else 0
        )
        cpu_util = (
            self.allocated.cpu_cores / self.capacity.cpu_cores if self.capacity.cpu_cores > 0 else 0
        )
        return (mem_util + cpu_util) / 2

    def can_allocate(self, resources: ResourceAllocation) -> bool:
        return (
            self.available_memory >= resources.memory_mb
            and self.available_cpu >= resources.cpu_cores
        )

    def allocate(self, resources: ResourceAllocation) -> bool:
        if not self.can_allocate(resources):
            return False
        self.allocated.memory_mb += resources.memory_mb
        self.allocated.cpu_cores += resources.cpu_cores
        self.agent_count += 1
        return True

    def deallocate(self, resources: ResourceAllocation) -> None:
        self.allocated.memory_mb = max(0, self.allocated.memory_mb - resources.memory_mb)
        self.allocated.cpu_cores = max(0, self.allocated.cpu_cores - resources.cpu_cores)
        self.agent_count = max(0, self.agent_count - 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "status": self.status,
            "capacity": self.capacity.to_dict(),
            "allocated": self.allocated.to_dict(),
            "agent_count": self.agent_count,
            "region": self.region,
            "tags": self.tags,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "utilization": self.utilization,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeNode":
        node = cls(
            node_id=data["node_id"],
            name=data["name"],
            host=data["host"],
            port=data["port"],
            status=data.get("status", "active"),
            capacity=ResourceAllocation.from_dict(data.get("capacity", {})),
            allocated=ResourceAllocation.from_dict(data.get("allocated", {})),
            agent_count=data.get("agent_count", 0),
            region=data.get("region", "default"),
            tags=data.get("tags", []),
        )
        if data.get("last_heartbeat"):
            node.last_heartbeat = datetime.fromisoformat(data["last_heartbeat"])
        return node


class AgentOSRuntime:
    """
    Agent-OS Runtime Manager for RRA.

    Handles distributed deployment, lifecycle management, and
    orchestration of RRA agents across the cluster.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/agent_os")
        self.nodes: Dict[str, RuntimeNode] = {}
        self.instances: Dict[str, AgentInstance] = {}
        self.deployments: Dict[str, str] = {}  # repo_id -> instance_id

        if data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._load_state()
        else:
            self._register_local_node()

    def _generate_id(self, prefix: str = "") -> str:
        return f"{prefix}{secrets.token_hex(8)}"

    def _register_local_node(self) -> None:
        """Register local node for standalone mode."""
        node = RuntimeNode(
            node_id="local",
            name="Local Node",
            host="localhost",
            port=8080,
            status="active",
        )
        self.nodes[node.node_id] = node

    # =========================================================================
    # Node Management
    # =========================================================================

    def register_node(
        self,
        name: str,
        host: str,
        port: int,
        capacity: Optional[ResourceAllocation] = None,
        region: str = "default",
        tags: Optional[List[str]] = None,
    ) -> RuntimeNode:
        """Register a new runtime node."""
        node = RuntimeNode(
            node_id=self._generate_id("node_"),
            name=name,
            host=host,
            port=port,
            capacity=capacity or ResourceAllocation(8192, 8.0, 100000, 1000),
            region=region,
            tags=tags or [],
            last_heartbeat=datetime.now(),
        )

        self.nodes[node.node_id] = node
        self._save_state()

        return node

    def get_node(self, node_id: str) -> Optional[RuntimeNode]:
        return self.nodes.get(node_id)

    def list_nodes(self, active_only: bool = True) -> List[RuntimeNode]:
        """List runtime nodes."""
        nodes = list(self.nodes.values())
        if active_only:
            nodes = [n for n in nodes if n.status == "active"]
        return nodes

    def update_node_heartbeat(self, node_id: str) -> RuntimeNode:
        """Update node heartbeat."""
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"Node not found: {node_id}")

        node.last_heartbeat = datetime.now()
        self._save_state()

        return node

    def select_node(
        self,
        resources: ResourceAllocation,
        preferred_region: Optional[str] = None,
        required_tags: Optional[List[str]] = None,
    ) -> Optional[RuntimeNode]:
        """Select best node for deployment."""
        candidates = []

        for node in self.nodes.values():
            if node.status != "active":
                continue

            if not node.can_allocate(resources):
                continue

            if preferred_region and node.region != preferred_region:
                continue

            if required_tags and not all(t in node.tags for t in required_tags):
                continue

            candidates.append(node)

        if not candidates:
            return None

        # Sort by utilization (prefer less utilized nodes)
        candidates.sort(key=lambda n: n.utilization)
        return candidates[0]

    # =========================================================================
    # Agent Deployment
    # =========================================================================

    def deploy_agent(self, config: AgentConfig, node_id: Optional[str] = None) -> AgentInstance:
        """Deploy a new agent instance."""
        # Select node if not specified
        if node_id:
            node = self.nodes.get(node_id)
            if not node:
                raise ValueError(f"Node not found: {node_id}")
        else:
            node = self.select_node(config.resources)
            if not node:
                raise ValueError("No suitable node available")

        # Allocate resources
        if not node.allocate(config.resources):
            raise ValueError(f"Insufficient resources on node: {node.node_id}")

        # Create instance
        instance = AgentInstance(
            instance_id=self._generate_id("agent_"),
            config=config,
            status=AgentStatus.PENDING,
            node_id=node.node_id,
            created_at=datetime.now(),
        )

        self.instances[instance.instance_id] = instance

        # Track repo deployment
        if config.repo_id:
            self.deployments[config.repo_id] = instance.instance_id

        self._save_state()

        return instance

    def start_agent(self, instance_id: str) -> AgentInstance:
        """Start an agent instance."""
        instance = self.instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance not found: {instance_id}")

        if instance.status not in (AgentStatus.PENDING, AgentStatus.STOPPED, AgentStatus.PAUSED):
            raise ValueError(f"Cannot start agent in status: {instance.status.value}")

        instance.status = AgentStatus.STARTING
        instance.started_at = datetime.now()

        # Simulate startup (in production would connect to node)
        instance.status = AgentStatus.RUNNING
        instance.health_status = "healthy"
        instance.last_health_check = datetime.now()

        self._save_state()

        return instance

    def stop_agent(self, instance_id: str) -> AgentInstance:
        """Stop an agent instance."""
        instance = self.instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance not found: {instance_id}")

        if instance.status not in (AgentStatus.RUNNING, AgentStatus.PAUSED):
            raise ValueError(f"Cannot stop agent in status: {instance.status.value}")

        instance.status = AgentStatus.STOPPING
        instance.stopped_at = datetime.now()

        # Release resources
        node = self.nodes.get(instance.node_id)
        if node:
            node.deallocate(instance.config.resources)

        instance.status = AgentStatus.STOPPED

        self._save_state()

        return instance

    def restart_agent(self, instance_id: str) -> AgentInstance:
        """Restart an agent instance."""
        instance = self.instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance not found: {instance_id}")

        if instance.restart_count >= instance.config.max_restarts:
            instance.status = AgentStatus.FAILED
            instance.error_message = "Max restarts exceeded"
            self._save_state()
            raise ValueError("Max restart limit reached")

        # Stop and start
        if instance.status == AgentStatus.RUNNING:
            instance.status = AgentStatus.STOPPING

        instance.restart_count += 1
        instance.status = AgentStatus.STARTING
        instance.started_at = datetime.now()
        instance.status = AgentStatus.RUNNING
        instance.health_status = "healthy"
        instance.last_health_check = datetime.now()
        instance.error_message = None

        self._save_state()

        return instance

    def terminate_agent(self, instance_id: str) -> AgentInstance:
        """Terminate and remove an agent instance."""
        instance = self.instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance not found: {instance_id}")

        # Stop if running
        if instance.status == AgentStatus.RUNNING:
            self.stop_agent(instance_id)

        instance.status = AgentStatus.TERMINATED

        # Remove deployment tracking
        if instance.config.repo_id:
            if self.deployments.get(instance.config.repo_id) == instance_id:
                del self.deployments[instance.config.repo_id]

        self._save_state()

        return instance

    def get_instance(self, instance_id: str) -> Optional[AgentInstance]:
        return self.instances.get(instance_id)

    def get_instance_by_repo(self, repo_id: str) -> Optional[AgentInstance]:
        """Get instance for a repository."""
        instance_id = self.deployments.get(repo_id)
        if instance_id:
            return self.instances.get(instance_id)
        return None

    def list_instances(
        self,
        status: Optional[AgentStatus] = None,
        agent_type: Optional[AgentType] = None,
        node_id: Optional[str] = None,
    ) -> List[AgentInstance]:
        """List agent instances with filters."""
        instances = list(self.instances.values())

        if status:
            instances = [i for i in instances if i.status == status]

        if agent_type:
            instances = [i for i in instances if i.config.agent_type == agent_type]

        if node_id:
            instances = [i for i in instances if i.node_id == node_id]

        return instances

    # =========================================================================
    # Health & Monitoring
    # =========================================================================

    def update_health(
        self, instance_id: str, health_status: str, metrics: Optional[Dict[str, Any]] = None
    ) -> AgentInstance:
        """Update agent health status."""
        instance = self.instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance not found: {instance_id}")

        instance.health_status = health_status
        instance.last_health_check = datetime.now()
        if metrics:
            instance.metrics = metrics

        # Handle unhealthy agents
        if health_status == "unhealthy" and instance.config.auto_restart:
            if instance.restart_count < instance.config.max_restarts:
                self.restart_agent(instance_id)

        self._save_state()

        return instance

    async def health_check_loop(self, interval_seconds: int = 60) -> None:
        """Run health checks on all instances."""
        while True:
            for instance in self.instances.values():
                if instance.status == AgentStatus.RUNNING:
                    # In production, would actually check agent health
                    if instance.last_health_check:
                        age = (datetime.now() - instance.last_health_check).total_seconds()
                        if age > instance.config.health_check_interval_seconds * 3:
                            instance.health_status = "unhealthy"

            await asyncio.sleep(interval_seconds)

    # =========================================================================
    # Scaling
    # =========================================================================

    def scale_agent(self, config: AgentConfig, replicas: int) -> List[AgentInstance]:
        """Scale an agent to specified number of replicas."""
        # Find existing instances for this config
        existing = [
            i
            for i in self.instances.values()
            if i.config.name == config.name
            and i.status in (AgentStatus.RUNNING, AgentStatus.PENDING, AgentStatus.STARTING)
        ]

        current_count = len(existing)
        instances = list(existing)

        if replicas > current_count:
            # Scale up
            for _ in range(replicas - current_count):
                new_instance = self.deploy_agent(config)
                self.start_agent(new_instance.instance_id)
                instances.append(new_instance)

        elif replicas < current_count:
            # Scale down
            to_stop = current_count - replicas
            for instance in existing[:to_stop]:
                self.terminate_agent(instance.instance_id)
                instances.remove(instance)

        return instances

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_cluster_stats(self) -> Dict[str, Any]:
        """Get cluster-wide statistics."""
        active_nodes = [n for n in self.nodes.values() if n.status == "active"]
        running_instances = [i for i in self.instances.values() if i.status == AgentStatus.RUNNING]
        healthy_instances = [i for i in running_instances if i.is_healthy]

        total_memory = sum(n.capacity.memory_mb for n in active_nodes)
        used_memory = sum(n.allocated.memory_mb for n in active_nodes)
        total_cpu = sum(n.capacity.cpu_cores for n in active_nodes)
        used_cpu = sum(n.allocated.cpu_cores for n in active_nodes)

        return {
            "total_nodes": len(self.nodes),
            "active_nodes": len(active_nodes),
            "total_instances": len(self.instances),
            "running_instances": len(running_instances),
            "healthy_instances": len(healthy_instances),
            "pending_instances": len(
                [i for i in self.instances.values() if i.status == AgentStatus.PENDING]
            ),
            "failed_instances": len(
                [i for i in self.instances.values() if i.status == AgentStatus.FAILED]
            ),
            "total_memory_mb": total_memory,
            "used_memory_mb": used_memory,
            "memory_utilization": (used_memory / total_memory * 100) if total_memory > 0 else 0,
            "total_cpu_cores": total_cpu,
            "used_cpu_cores": used_cpu,
            "cpu_utilization": (used_cpu / total_cpu * 100) if total_cpu > 0 else 0,
            "deployments": len(self.deployments),
        }

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save_state(self) -> None:
        if not self.data_dir:
            return

        state = {
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "instances": {iid: i.to_dict() for iid, i in self.instances.items()},
            "deployments": self.deployments,
        }

        with open(self.data_dir / "agent_os_state.json", "w") as f:
            json.dump(state, f, indent=2, default=str)

    def _load_state(self) -> None:
        state_file = self.data_dir / "agent_os_state.json"
        if not state_file.exists():
            self._register_local_node()
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            self.nodes = {
                nid: RuntimeNode.from_dict(n) for nid, n in state.get("nodes", {}).items()
            }
            self.instances = {
                iid: AgentInstance.from_dict(i) for iid, i in state.get("instances", {}).items()
            }
            self.deployments = state.get("deployments", {})

            if not self.nodes:
                self._register_local_node()
        except (json.JSONDecodeError, KeyError):
            self._register_local_node()


def create_agent_os_runtime(data_dir: Optional[str] = None) -> AgentOSRuntime:
    """Factory function to create an Agent-OS runtime."""
    path = Path(data_dir) if data_dir else None
    return AgentOSRuntime(data_dir=path)

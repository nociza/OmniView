from __future__ import annotations

from datetime import UTC, datetime
from threading import RLock

from omniview.config import Settings
from omniview.models import AgentReport, ClientRecord, ClientReport, ClientView, DashboardCounts, DashboardResponse, DashboardSummary, NodeProfile, NodeRecord, NodeStatus, NodeView, TelemetryPayload
from omniview.services.dispatch import build_launches


_STATUS_ORDER = {
    NodeStatus.ONLINE: 0,
    NodeStatus.STALE: 1,
    NodeStatus.OFFLINE: 2,
}


class NodeNotFoundError(KeyError):
    pass


class ClientNotFoundError(KeyError):
    pass


class NodeRegistry:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._records: dict[str, NodeRecord] = {}
        self._clients: dict[str, ClientRecord] = {}
        self._lock = RLock()

    def seed(self, records: list[NodeRecord]) -> None:
        with self._lock:
            self._records = {record.profile.node_id: record for record in records}

    def seed_clients(self, records: list[ClientRecord]) -> None:
        with self._lock:
            self._clients = {record.profile.client_id: record for record in records}

    def upsert_profile(self, profile: NodeProfile) -> NodeView:
        with self._lock:
            now = datetime.now(UTC)
            existing = self._records.get(profile.node_id)
            telemetry = existing.telemetry if existing else None
            registered_at = existing.registered_at if existing else now
            record = NodeRecord(profile=profile, telemetry=telemetry, registered_at=registered_at, last_seen_at=now)
            self._records[profile.node_id] = record
            self._prune_nodes()
            return self._build_view(record, now)

    def record_telemetry(self, node_id: str, telemetry: TelemetryPayload) -> NodeView:
        with self._lock:
            record = self._records.get(node_id)
            if record is None:
                raise NodeNotFoundError(node_id)
            now = datetime.now(UTC)
            updated = record.model_copy(update={"telemetry": telemetry, "last_seen_at": now})
            self._records[node_id] = updated
            return self._build_view(updated, now)

    def ingest_report(self, report: AgentReport) -> NodeView:
        with self._lock:
            now = datetime.now(UTC)
            existing = self._records.get(report.profile.node_id)
            registered_at = existing.registered_at if existing else now
            record = NodeRecord(
                profile=report.profile,
                telemetry=report.telemetry,
                registered_at=registered_at,
                last_seen_at=now,
            )
            self._records[report.profile.node_id] = record
            self._prune_nodes()
            return self._build_view(record, now)

    def ingest_client_report(self, report: ClientReport) -> ClientView:
        with self._lock:
            now = datetime.now(UTC)
            existing = self._clients.get(report.profile.client_id)
            registered_at = existing.registered_at if existing else now
            record = ClientRecord(
                profile=report.profile,
                telemetry=report.telemetry,
                registered_at=registered_at,
                last_seen_at=now,
            )
            self._clients[report.profile.client_id] = record
            self._prune_clients()
            return self._build_client_view(record, now)

    def list_nodes(self) -> list[NodeView]:
        with self._lock:
            now = datetime.now(UTC)
            views = [self._build_view(record, now) for record in self._records.values()]
            return sorted(views, key=self._sort_key)

    def list_clients(self) -> list[ClientView]:
        with self._lock:
            now = datetime.now(UTC)
            views = [self._build_client_view(record, now) for record in self._clients.values()]
            return sorted(views, key=self._sort_client_key)

    def get_node(self, node_id: str) -> NodeView:
        with self._lock:
            record = self._records.get(node_id)
            if record is None:
                raise NodeNotFoundError(node_id)
            return self._build_view(record, datetime.now(UTC))

    def get_client(self, client_id: str) -> ClientView:
        with self._lock:
            record = self._clients.get(client_id)
            if record is None:
                raise ClientNotFoundError(client_id)
            return self._build_client_view(record, datetime.now(UTC))

    def dashboard(self) -> DashboardResponse:
        nodes = self.list_nodes()
        clients = self.list_clients()
        counts = DashboardCounts(
            total=len(nodes),
            online=sum(1 for node in nodes if node.status is NodeStatus.ONLINE),
            stale=sum(1 for node in nodes if node.status is NodeStatus.STALE),
            offline=sum(1 for node in nodes if node.status is NodeStatus.OFFLINE),
        )

        cpu_values = [node.telemetry.metrics.cpu_percent for node in nodes if node.telemetry is not None]
        hottest = max(
            (
                (node.name, node.telemetry.metrics.temperature_c)
                for node in nodes
                if node.telemetry is not None and node.telemetry.metrics.temperature_c is not None
            ),
            key=lambda item: item[1],
            default=None,
        )

        summary = DashboardSummary(
            counts=counts,
            average_cpu_percent=round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else None,
            hottest_node_name=hottest[0] if hottest else None,
            last_updated_at=datetime.now(UTC),
        )
        return DashboardResponse(summary=summary, nodes=nodes, clients=clients, poll_interval_seconds=self._settings.poll_interval_seconds)

    def _build_view(self, record: NodeRecord, now: datetime) -> NodeView:
        age_seconds = max(0, int((now - record.last_seen_at).total_seconds()))
        status = self._status_for_age(age_seconds)
        launches = build_launches(record.profile.name, record.profile.overlay_ip, record.profile.protocols)
        return NodeView(
            node_id=record.profile.node_id,
            name=record.profile.name,
            hostname=record.profile.hostname,
            overlay_ip=record.profile.overlay_ip,
            platform=record.profile.platform,
            description=record.profile.description,
            location=record.profile.location,
            tags=record.profile.tags,
            headless=record.profile.headless,
            agent_version=record.profile.agent_version,
            status=status,
            status_message=self._status_message(status=status, age_seconds=age_seconds, has_telemetry=record.telemetry is not None),
            last_seen_at=record.last_seen_at,
            heartbeat_age_seconds=age_seconds,
            preferred_protocol=launches[0].kind if launches else None,
            protocols=launches,
            telemetry=record.telemetry,
        )

    def _build_client_view(self, record: ClientRecord, now: datetime) -> ClientView:
        age_seconds = max(0, int((now - record.last_seen_at).total_seconds()))
        status = self._status_for_age(age_seconds)
        return ClientView(
            client_id=record.profile.client_id,
            name=record.profile.name,
            hostname=record.profile.hostname,
            overlay_ip=record.profile.overlay_ip,
            platform=record.profile.platform,
            hub_url=record.profile.hub_url,
            launcher_url=record.profile.launcher_url,
            app_version=record.profile.app_version,
            status=status,
            status_message=self._status_message(status=status, age_seconds=age_seconds, has_telemetry=record.telemetry is not None),
            last_seen_at=record.last_seen_at,
            heartbeat_age_seconds=age_seconds,
            capabilities=record.profile.capabilities,
            telemetry=record.telemetry,
        )

    def _status_for_age(self, age_seconds: int) -> NodeStatus:
        if age_seconds <= self._settings.online_ttl_seconds:
            return NodeStatus.ONLINE
        if age_seconds <= self._settings.stale_ttl_seconds:
            return NodeStatus.STALE
        return NodeStatus.OFFLINE

    @staticmethod
    def _status_message(*, status: NodeStatus, age_seconds: int, has_telemetry: bool) -> str:
        if not has_telemetry:
            return "Registered, awaiting first telemetry payload."
        if status is NodeStatus.ONLINE:
            return f"Fresh telemetry {age_seconds}s ago."
        if status is NodeStatus.STALE:
            return f"Signal degraded, last update {age_seconds}s ago."
        return f"Node considered offline, last update {age_seconds}s ago."

    @staticmethod
    def _sort_key(node: NodeView) -> tuple[int, int, str]:
        telemetry_priority = 0 if node.telemetry is not None else 1
        return (_STATUS_ORDER[node.status], telemetry_priority, node.name.lower())

    @staticmethod
    def _sort_client_key(client: ClientView) -> tuple[int, int, str]:
        telemetry_priority = 0 if client.telemetry is not None else 1
        return (_STATUS_ORDER[client.status], telemetry_priority, client.name.lower())

    def _prune_nodes(self) -> None:
        overflow = len(self._records) - self._settings.max_nodes
        if overflow <= 0:
            return
        for node_id, _record in sorted(self._records.items(), key=lambda item: item[1].last_seen_at)[:overflow]:
            self._records.pop(node_id, None)

    def _prune_clients(self) -> None:
        overflow = len(self._clients) - self._settings.max_clients
        if overflow <= 0:
            return
        for client_id, _record in sorted(self._clients.items(), key=lambda item: item[1].last_seen_at)[:overflow]:
            self._clients.pop(client_id, None)

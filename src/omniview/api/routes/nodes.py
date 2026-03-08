from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from omniview.api.deps import get_registry
from omniview.models import AgentReport, DashboardResponse, NodeProfile, NodeView, TelemetryPayload
from omniview.store import NodeNotFoundError, NodeRegistry

router = APIRouter(tags=["nodes"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(registry: NodeRegistry = Depends(get_registry)) -> DashboardResponse:
    return registry.dashboard()


@router.get("/nodes", response_model=list[NodeView])
def list_nodes(registry: NodeRegistry = Depends(get_registry)) -> list[NodeView]:
    return registry.list_nodes()


@router.get("/nodes/{node_id}", response_model=NodeView)
def get_node(node_id: str, registry: NodeRegistry = Depends(get_registry)) -> NodeView:
    try:
        return registry.get_node(node_id)
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown node '{node_id}'.") from exc


@router.post("/nodes/register", response_model=NodeView, status_code=status.HTTP_201_CREATED)
def register_node(profile: NodeProfile, registry: NodeRegistry = Depends(get_registry)) -> NodeView:
    return registry.upsert_profile(profile)


@router.post("/nodes/{node_id}/telemetry", response_model=NodeView)
def update_telemetry(
    node_id: str,
    telemetry: TelemetryPayload,
    registry: NodeRegistry = Depends(get_registry),
) -> NodeView:
    try:
        return registry.record_telemetry(node_id, telemetry)
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown node '{node_id}'.") from exc


@router.post("/agent/report", response_model=NodeView, status_code=status.HTTP_202_ACCEPTED)
def report_agent(report: AgentReport, registry: NodeRegistry = Depends(get_registry)) -> NodeView:
    return registry.ingest_report(report)

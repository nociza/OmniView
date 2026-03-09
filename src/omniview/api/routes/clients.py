from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from omniview.api.deps import get_registry
from omniview.models import ClientReport, ClientView
from omniview.store import ClientNotFoundError, NodeRegistry

router = APIRouter(tags=["clients"])


@router.get("/clients", response_model=list[ClientView])
def list_clients(registry: NodeRegistry = Depends(get_registry)) -> list[ClientView]:
    return registry.list_clients()


@router.get("/clients/{client_id}", response_model=ClientView)
def get_client(client_id: str, registry: NodeRegistry = Depends(get_registry)) -> ClientView:
    try:
        return registry.get_client(client_id)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown client '{client_id}'.") from exc


@router.post("/clients/report", response_model=ClientView, status_code=status.HTTP_202_ACCEPTED)
def report_client(report: ClientReport, registry: NodeRegistry = Depends(get_registry)) -> ClientView:
    return registry.ingest_client_report(report)

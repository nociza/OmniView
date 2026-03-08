from __future__ import annotations

from fastapi import Request

from omniview.store import NodeRegistry


def get_registry(request: Request) -> NodeRegistry:
    return request.app.state.registry

"""
Unit tests for the extension PluginRegistry.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.events import EventBus
from app.core.hooks import HookPoint, HookRegistry
from app.core.plugins import BasePlugin, PluginRegistry


class MockClientCustomPlugin(BasePlugin):
    name = "custom_discount_rule"
    version = "1.2.0"

    def __init__(self, tenant_id: uuid.UUID | None = None) -> None:
        self.tenant_id = tenant_id
        self.is_setup = False

    async def setup(self, hooks: HookRegistry, events: EventBus) -> None:
        self.is_setup = True
        hooks.register(
            HookPoint.PRE_INVOICE_GENERATE,
            lambda ctx: ctx.data.update({"discount": 0.1}),
            tenant_id=self.tenant_id,
        )


@pytest.mark.unit
async def test_plugin_registration_and_initialization() -> None:
    """Verifica cadastro, listagem filtrada e inicialização de plugins."""
    catalog = PluginRegistry()
    t1 = uuid.uuid4()
    t2 = uuid.uuid4()

    plugin_global = MockClientCustomPlugin()
    plugin_global.name = "global_audit_plugin"

    plugin_tenant1 = MockClientCustomPlugin(tenant_id=t1)
    plugin_tenant1.name = "tenant1_rule"

    catalog.register(plugin_global)
    catalog.register(plugin_tenant1)

    assert catalog.get_plugin("global_audit_plugin") == plugin_global
    assert catalog.get_plugin("tenant1_rule") == plugin_tenant1

    # Listagem por tenant
    plugins_for_t1 = catalog.list_plugins(tenant_id=t1)
    assert len(plugins_for_t1) == 2  # Global + Tenant 1

    plugins_for_t2 = catalog.list_plugins(tenant_id=t2)
    assert len(plugins_for_t2) == 1  # Apenas o global
    assert plugins_for_t2[0] == plugin_global

    # Inicialização
    test_hooks = HookRegistry()
    test_events = EventBus()
    await catalog.initialize_all(hooks=test_hooks, events=test_events)

    assert plugin_global.is_setup is True
    assert plugin_tenant1.is_setup is True

    # Desregistro
    catalog.unregister("global_audit_plugin")
    assert catalog.get_plugin("global_audit_plugin") is None

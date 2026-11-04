"""
EBA — Plugin Architecture
Framework de extensibilidade para acoplamento de integrações sob demanda.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

import structlog

from app.core.events import EventBus, event_bus
from app.core.hooks import HookRegistry, hook_registry

logger = structlog.get_logger(__name__)


class BasePlugin(ABC):
    """Classe base abstrata para plugins de clientes e integrações customizadas."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    tenant_id: UUID | None = None  # None = disponível globalmente

    @abstractmethod
    async def setup(self, hooks: HookRegistry, events: EventBus) -> None:
        """Inicializa o plugin, registrando hooks e ouvintes de eventos."""
        raise NotImplementedError

    async def teardown(self) -> None:  # noqa: B027
        """Limpa recursos do plugin."""
        return


class PluginRegistry:
    """Catálogo e gerenciador de ciclo de vida dos plugins ativos."""

    def __init__(self) -> None:
        self._plugins: dict[str, BasePlugin] = {}

    def register(self, plugin: BasePlugin) -> None:
        """Registra um plugin no catálogo."""
        self._plugins[plugin.name] = plugin
        logger.info(
            "Plugin registered in catalog",
            plugin=plugin.name,
            version=plugin.version,
            tenant_id=str(plugin.tenant_id) if plugin.tenant_id else "global",
        )

    def unregister(self, plugin_name: str) -> None:
        """Remove um plugin do catálogo."""
        if plugin_name in self._plugins:
            del self._plugins[plugin_name]

    def get_plugin(self, plugin_name: str) -> BasePlugin | None:
        """Obtém um plugin pelo nome."""
        return self._plugins.get(plugin_name)

    def list_plugins(self, tenant_id: UUID | None = None) -> list[BasePlugin]:
        """Lista plugins disponíveis para um tenant específico (inclui plugins globais)."""
        if tenant_id is None:
            return list(self._plugins.values())
        return [
            p for p in self._plugins.values() if p.tenant_id is None or p.tenant_id == tenant_id
        ]

    async def initialize_all(
        self,
        hooks: HookRegistry | None = None,
        events: EventBus | None = None,
    ) -> None:
        """Inicializa todos os plugins registrados."""
        h = hooks or hook_registry
        e = events or event_bus
        for plugin in self._plugins.values():
            try:
                await plugin.setup(h, e)
                logger.info("Plugin setup completed", plugin=plugin.name)
            except Exception as exc:
                logger.error(
                    "Failed to setup plugin",
                    plugin=plugin.name,
                    error=str(exc),
                )


# Instância global do catálogo de plugins
plugin_registry = PluginRegistry()

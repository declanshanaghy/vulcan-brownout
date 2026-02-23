"""Config flow for Vulcan Brownout integration."""

import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class VulcanBrownoutConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Vulcan Brownout integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id("vulcan_brownout_unique")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Vulcan Brownout", data={}, options={}
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={
                "integration_name": "Vulcan Brownout",
            },
        )

    async def async_step_import(
        self, import_data: Dict[str, Any]
    ) -> FlowResult:
        """Import from YAML configuration."""
        return await self.async_step_user(import_data)

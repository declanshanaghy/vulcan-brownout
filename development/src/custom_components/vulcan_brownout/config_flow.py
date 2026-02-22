"""Config flow for Vulcan Brownout integration."""

import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import (
    DOMAIN,
    BATTERY_THRESHOLD_DEFAULT,
    BATTERY_THRESHOLD_MIN,
    BATTERY_THRESHOLD_MAX,
    MAX_DEVICE_RULES,
)

_LOGGER = logging.getLogger(__name__)


class VulcanBrownoutConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Vulcan Brownout integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Minimal config - battery entities auto-discovered
            await self.async_set_unique_id("vulcan_brownout_unique")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="Vulcan Brownout",
                data={},
                options={
                    "global_threshold": BATTERY_THRESHOLD_DEFAULT,
                    "device_rules": {},
                },
            )

        # Show a simple form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={
                "integration_name": "Vulcan Brownout",
            },
        )

    async def async_step_import(self, import_data: Dict[str, Any]) -> FlowResult:
        """Import from YAML configuration (if needed)."""
        return await self.async_step_user(import_data)

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return options flow for configuration."""
        return VulcanBrownoutOptionsFlow(config_entry)


class VulcanBrownoutOptionsFlow(config_entries.OptionsFlow):
    """Options flow for threshold configuration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle options step."""
        if user_input is not None:
            # Validate inputs
            global_threshold = user_input.get("global_threshold", BATTERY_THRESHOLD_DEFAULT)

            # Validate global threshold
            if not (BATTERY_THRESHOLD_MIN <= global_threshold <= BATTERY_THRESHOLD_MAX):
                return self.async_show_form(
                    step_id="init",
                    data_schema=vol.Schema(
                        {
                            vol.Optional(
                                "global_threshold",
                                default=self.config_entry.options.get(
                                    "global_threshold", BATTERY_THRESHOLD_DEFAULT
                                ),
                            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=100)),
                        }
                    ),
                    errors={"global_threshold": "invalid_range"},
                    description_placeholders={
                        "min": "5",
                        "max": "100",
                    },
                )

            # Return options (device rules managed via WebSocket in Sprint 2)
            return self.async_create_entry(
                title="Threshold Settings",
                data={
                    "global_threshold": global_threshold,
                    "device_rules": self.config_entry.options.get("device_rules", {}),
                },
            )

        # Show form with current values
        current_options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "global_threshold",
                        default=current_options.get("global_threshold", BATTERY_THRESHOLD_DEFAULT),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=100)),
                }
            ),
            description_placeholders={
                "info": "Global threshold for all battery devices. "
                "Individual devices can override this setting."
            },
        )

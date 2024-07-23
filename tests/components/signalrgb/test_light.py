"""Unit tests for the SignalRGB component."""

import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.components.signalrgb import async_setup_entry, async_unload_entry
from homeassistant.components.signalrgb.const import (
    ALL_OFF_EFFECT,
    DEFAULT_EFFECT,
    DEFAULT_PORT,
    DOMAIN,
)
from homeassistant.components.signalrgb.light import SignalRGBLight
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

PLATFORMS = ["light"]


@pytest.fixture
def mock_signalrgb_client():
    """Mock SignalRGB client."""
    with patch("homeassistant.components.signalrgb.SignalRGBClient") as mock_client:
        yield mock_client


@pytest.fixture
def mock_config_entry():
    """Mock configuration entry."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="SignalRGB",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: DEFAULT_PORT,
        },
        source="user",
        entry_id="test",
        options={},
        unique_id=f"192.168.1.100:{DEFAULT_PORT}",
    )


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.async_add_executor_job = AsyncMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.loop_thread_id = threading.get_ident()

    # Mock the states attribute
    mock_states = MagicMock()
    mock_states.async_set_internal = AsyncMock()
    hass.states = mock_states

    return hass


async def test_setup_entry(mock_hass, mock_config_entry, mock_signalrgb_client):
    """Test setting up the SignalRGB integration."""
    mock_client = mock_signalrgb_client.return_value
    mock_client.get_current_effect = MagicMock()

    assert await async_setup_entry(mock_hass, mock_config_entry)
    assert DOMAIN in mock_hass.data
    assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
    assert isinstance(mock_hass.data[DOMAIN][mock_config_entry.entry_id], MagicMock)
    assert len(mock_hass.config_entries.async_forward_entry_setups.mock_calls) == 1
    assert (
        mock_hass.config_entries.async_forward_entry_setups.mock_calls[0][1][1]
        == PLATFORMS
    )


async def test_unload_entry(mock_hass, mock_config_entry):
    """Test unloading the SignalRGB integration."""
    mock_hass.data[DOMAIN] = {mock_config_entry.entry_id: MagicMock()}

    assert await async_unload_entry(mock_hass, mock_config_entry)
    assert mock_config_entry.entry_id not in mock_hass.data[DOMAIN]


class TestSignalRGBLight:
    """Test class for SignalRGBLight."""

    @pytest.fixture
    def mock_light(self, mock_hass, mock_signalrgb_client, mock_config_entry):
        """Mock SignalRGBLight instance."""
        client = mock_signalrgb_client.return_value
        light = SignalRGBLight(client, mock_config_entry)
        light.hass = mock_hass
        light.entity_id = "light.signalrgb"
        return light

    async def test_turn_on(self, mock_light):
        """Test turning on the light."""
        mock_light.hass.async_add_executor_job.return_value = None
        await mock_light.async_turn_on()
        assert mock_light.is_on
        mock_light.hass.async_add_executor_job.assert_called_once_with(
            mock_light._client.apply_effect_by_name, DEFAULT_EFFECT
        )

    async def test_turn_off(self, mock_light):
        """Test turning off the light."""
        mock_light.hass.async_add_executor_job.return_value = None
        await mock_light.async_turn_off()
        assert not mock_light.is_on
        mock_light.hass.async_add_executor_job.assert_called_once_with(
            mock_light._client.apply_effect_by_name, ALL_OFF_EFFECT
        )

    async def test_effect_list(self, mock_light):
        """Test getting the effect list."""
        mock_effect = MagicMock()
        mock_effect.attributes.name = "Test Effect"
        mock_light.hass.async_add_executor_job.side_effect = [
            [mock_effect],  # For get_effects
            mock_effect,  # For get_current_effect
        ]

        await mock_light.async_update()
        assert mock_light.effect_list == ["Test Effect"]

    async def test_apply_effect(self, mock_light):
        """Test applying an effect."""
        mock_light.hass.async_add_executor_job.return_value = None
        await mock_light._apply_effect("Test Effect")
        mock_light.hass.async_add_executor_job.assert_called_once_with(
            mock_light._client.apply_effect_by_name, "Test Effect"
        )
        assert mock_light.effect == "Test Effect"

    async def test_update(self, mock_light):
        """Test updating the light state."""
        mock_effect = MagicMock()
        mock_effect.attributes.name = "Current Effect"
        mock_light.hass.async_add_executor_job.side_effect = [
            [],  # For get_effects (empty list as it's already populated)
            mock_effect,  # For get_current_effect
        ]

        await mock_light.async_update()
        assert mock_light.is_on
        assert mock_light.effect == "Current Effect"

        # Test with ALL_OFF_EFFECT
        mock_effect.attributes.name = ALL_OFF_EFFECT
        mock_light.hass.async_add_executor_job.side_effect = [
            [],  # For get_effects (empty list as it's already populated)
            mock_effect,  # For get_current_effect
        ]
        await mock_light.async_update()
        assert not mock_light.is_on

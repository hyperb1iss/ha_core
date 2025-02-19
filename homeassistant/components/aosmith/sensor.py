"""The sensor platform for the A. O. Smith integration."""

from collections.abc import Callable
from dataclasses import dataclass

from py_aosmith.models import Device as AOSmithDevice

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import (
    AOSmithConfigEntry,
    AOSmithEnergyCoordinator,
    AOSmithStatusCoordinator,
)
from .entity import AOSmithEnergyEntity, AOSmithStatusEntity


@dataclass(frozen=True, kw_only=True)
class AOSmithStatusSensorEntityDescription(SensorEntityDescription):
    """Entity description class for sensors using data from the status coordinator."""

    value_fn: Callable[[AOSmithDevice], str | int | None]


STATUS_ENTITY_DESCRIPTIONS: tuple[AOSmithStatusSensorEntityDescription, ...] = (
    AOSmithStatusSensorEntityDescription(
        key="hot_water_availability",
        translation_key="hot_water_availability",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda device: device.status.hot_water_status,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AOSmithConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up A. O. Smith sensor platform."""
    data = entry.runtime_data

    async_add_entities(
        AOSmithStatusSensorEntity(data.status_coordinator, description, junction_id)
        for description in STATUS_ENTITY_DESCRIPTIONS
        for junction_id in data.status_coordinator.data
    )

    async_add_entities(
        AOSmithEnergySensorEntity(data.energy_coordinator, junction_id)
        for junction_id in data.status_coordinator.data
    )


class AOSmithStatusSensorEntity(AOSmithStatusEntity, SensorEntity):
    """Class for sensor entities that use data from the status coordinator."""

    entity_description: AOSmithStatusSensorEntityDescription

    def __init__(
        self,
        coordinator: AOSmithStatusCoordinator,
        description: AOSmithStatusSensorEntityDescription,
        junction_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, junction_id)
        self.entity_description = description
        self._attr_unique_id = f"{description.key}_{junction_id}"

    @property
    def native_value(self) -> str | int | None:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.device)


class AOSmithEnergySensorEntity(AOSmithEnergyEntity, SensorEntity):
    """Class for the energy sensor entity."""

    _attr_translation_key = "energy_usage"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        coordinator: AOSmithEnergyCoordinator,
        junction_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, junction_id)
        self._attr_unique_id = f"energy_usage_{junction_id}"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.energy_usage

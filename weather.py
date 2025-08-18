"""Weather platform for tenki.jp."""
from datetime import datetime, timedelta

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfSpeed,
    UnitOfPressure,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONDITION_MAP, DEFAULT_CONDITION, WIND_BEARING_MAP

def get_condition(weather_text: str | None, hour: int | None = None) -> str:
    if not weather_text: return DEFAULT_CONDITION
    if "雪" in weather_text: return "snowy"
    if "雨" in weather_text: return "rainy"
    is_night = hour is not None and (hour >= 18 or hour < 6)
    if "晴" in weather_text and "曇" in weather_text: return "partlycloudy"
    if "曇" in weather_text: return "cloudy"
    if "晴" in weather_text: return "clear-night" if is_night else "sunny"
    return DEFAULT_CONDITION

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TenkiJpWeather(coordinator, entry)])


class TenkiJpWeather(CoordinatorEntity, WeatherEntity):
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = UnitOfSpeed.METERS_PER_SECOND
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_name = entry.data["name"]
        self._attr_unique_id = entry.unique_id

    @property
    def condition(self) -> str | None:
        weather_text = self.coordinator.data.get("daily", {}).get("today", {}).get("weather")
        return get_condition(weather_text, datetime.now().hour)

    @property
    def native_temperature(self) -> float | None:
        return self.coordinator.data.get("current", {}).get("temperature")

    @property
    def humidity(self) -> int | None:
        return self.coordinator.data.get("current", {}).get("humidity")

    @property
    def native_pressure(self) -> float | None:
        return self.coordinator.data.get("current", {}).get("pressure")

    @property
    def native_wind_speed(self) -> float | None:
        return self.coordinator.data.get("current", {}).get("wind_speed")

    @property
    def wind_bearing(self) -> float | None:
        direction = self.coordinator.data.get("current", {}).get("wind_direction")
        return WIND_BEARING_MAP.get(direction)

    async def async_forecast_daily(self) -> list[Forecast] | None:
        forecast_data = self.coordinator.data.get("daily", {}).get("ten_day", [])
        forecasts = []
        today_data = self.coordinator.data.get("daily", {}).get("today", {})
        for idx, item in enumerate(forecast_data):
            condition = get_condition(item.get("weather"))
            forecast = {
                "datetime": item["date"],
                "condition": condition,
                "native_temperature": item.get("high_temp"),
                "native_templow": item.get("low_temp"),
                "precipitation_probability": item.get("prob_precip")
            }
            # 最初（今日）のデータだけtodayのhumidityをセット
            if idx == 0 and "humidity" in today_data:
                forecast["humidity"] = today_data["humidity"]
            forecasts.append(forecast)
        return forecasts

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        hourly_data = self.coordinator.data.get("hourly", {})
        if not hourly_data: return None
        forecasts = []
        now = datetime.now()
        
        today_str = now.strftime("%Y-%m-%d")
        today_hourly = hourly_data.get("today", [])
        for item in today_hourly:
            forecast_hour = item.get("time")
            if forecast_hour is None or forecast_hour <= now.hour: continue
            if forecast_hour == 24 and now.hour != 23: continue
            condition = get_condition(item.get("weather"), forecast_hour)
            bearing = WIND_BEARING_MAP.get(item.get("wind_direction"))
            forecasts.append({
                "datetime": f"{today_str}T{str(forecast_hour).zfill(2)}:00:00",
                "condition": condition,
                "native_temperature": item.get("temperature"),
                "precipitation_probability": item.get("prob_precip"),
                "native_precipitation": item.get("precipitation"),
                "humidity": item.get("humidity_percent"),
                "wind_bearing": bearing,
                "native_wind_speed": item.get("wind_speed")
            })
        
        tomorrow_date = now + timedelta(days=1)
        tomorrow_str = tomorrow_date.strftime("%Y-%m-%d")
        tomorrow_hourly = hourly_data.get("tomorrow", [])
        for item in tomorrow_hourly:
            forecast_hour = item.get("time")
            if forecast_hour is None or forecast_hour == 24: continue
            condition = get_condition(item.get("weather"), forecast_hour)
            bearing = WIND_BEARING_MAP.get(item.get("wind_direction"))
            forecasts.append({
                "datetime": f"{tomorrow_str}T{str(forecast_hour).zfill(2)}:00:00",
                "condition": condition,
                "native_temperature": item.get("temperature"),
                "precipitation_probability": item.get("prob_precip"),
                "native_precipitation": item.get("precipitation"),
                "humidity": item.get("humidity_percent"),
                "wind_bearing": bearing,
                "native_wind_speed": item.get("wind_speed")
            })

        return forecasts
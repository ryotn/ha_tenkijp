"""The tenki.jp weather integration."""
import asyncio
from datetime import datetime
import re
from datetime import timedelta
import logging

import async_timeout
import aiohttp
from bs4 import BeautifulSoup

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_URL_PATH

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["weather"]

def _parse_to_number(s: str | None) -> float | None:
    if s is None: return None
    try:
        s = "".join(filter(lambda c: c.isdigit() or c == '.' or c == '-', s))
        if not s: return None
        return float(s)
    except (ValueError, TypeError): return None

def _parse_prob_precip(s: str | None) -> int | None:
    if s is None or "---" in s: return None
    try:
        s = s.replace('%', '')
        if not s: return None
        return int(s)
    except (ValueError, TypeError): return None

async def async_fetch_data(session: aiohttp.ClientSession, url_path: str):
    base_url = "https://tenki.jp"
    urls = {"base": f"{base_url}{url_path}", "hourly": f"{base_url}{url_path}1hour.html", "tenday": f"{base_url}{url_path}10days.html"}
    async def get_page(url):
        async with async_timeout.timeout(15):
            response = await session.get(url)
            response.raise_for_status()
            return await response.text()
    try:
        html_base, html_hourly, html_tenday = await asyncio.gather(get_page(urls["base"]), get_page(urls["hourly"]), get_page(urls["tenday"]))
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        raise UpdateFailed(f"Error fetching data: {err}") from err
    soup_base = BeautifulSoup(html_base, "html.parser")
    soup_hourly = BeautifulSoup(html_hourly, "html.parser")
    soup_tenday = BeautifulSoup(html_tenday, "html.parser")
    hourly = _parse_hourly_forecast(soup_hourly)
    all_data = {"current": _parse_current_conditions(soup_base), "daily": _parse_daily_forecast(soup_base, soup_tenday, hourly), "hourly": hourly}
    try:
        current_hour = datetime.now().hour
        today_hourly = all_data["hourly"]["today"]
        for hour_data in today_hourly:
            if hour_data.get("time") == current_hour:
                all_data["current"]["humidity"] = hour_data.get("humidity_percent")
                break
    except (IndexError, KeyError, TypeError):
        _LOGGER.warning("Could not determine current humidity from hourly forecast")
    return all_data

def _parse_current_conditions(soup):
    live_box = soup.select_one('.live-box')
    if not live_box: return {}
    temp_text = live_box.select_one('.temp a').get_text(strip=True) if live_box.select_one('.temp a') else ""
    pressure_text = live_box.select_one('.pressure a').get_text(strip=True) if live_box.select_one('.pressure a') else ""
    wind_direction = None
    wind_a_tag = live_box.select_one('.wind a')
    if wind_a_tag:
        text_nodes = [text.strip() for text in wind_a_tag.find_all(string=True, recursive=False) if text.strip()]
        if text_nodes: wind_direction = text_nodes[0]
    wind_text = wind_a_tag.get_text(strip=True) if wind_a_tag else ""
    temp_match = re.search(r"(\d+\.\d+|\d+)", temp_text)
    wind_match = re.search(r"(\d+\.\d+|\d+)", wind_text)
    pressure_match = re.search(r"(\d+\.\d+|\d+)", pressure_text)
    return {"temperature": float(temp_match.group(1)) if temp_match else None, "wind_speed": float(wind_match.group(1)) if wind_match else None, "wind_direction": wind_direction, "pressure": float(pressure_match.group(1)) if pressure_match else None}

def _parse_daily_forecast(soup_base, soup_tenday, hourly):
    today_section = soup_base.select_one('.today-weather')
    today_forecast = {
        "weather": today_section.select_one('.weather-telop').text if today_section else None,
        "high_temp": _parse_to_number(today_section.select_one('.high-temp .value').text) if today_section else None,
        "low_temp": _parse_to_number(today_section.select_one('.low-temp .value').text) if today_section else None
    }
    # 毎時データから現時刻に近い湿度を取得
    now = datetime.now()
    today_hourly = hourly.get("today", [])
    humidity = None
    min_diff = 25
    for h in today_hourly:
        t = h.get("time")
        if t is not None:
            diff = abs(t - now.hour)
            if diff < min_diff and h.get("humidity_percent") is not None:
                min_diff = diff
                humidity = h.get("humidity_percent")
    if humidity is not None:
        today_forecast["humidity"] = humidity
    ten_day_forecast = []
    year = datetime.now().year
    last_month = 0
    for day_row in soup_tenday.select('.forecast10days-list .forecast10days-actab'):
        date_text = day_row.select_one('.days').text
        date_match = re.search(r'(\d{1,2})月(\d{1,2})日', date_text)
        if not date_match: continue
        month, day = int(date_match.group(1)), date_match.group(2)
        if month < last_month: year += 1
        last_month = month
        ten_day_forecast.append({
            "date": f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}",
            "weather": day_row.select_one('.forecast-telop').text,
            "high_temp": _parse_to_number(day_row.select_one('.high-temp').text),
            "low_temp": _parse_to_number(day_row.select_one('.low-temp').text),
            "prob_precip": _parse_prob_precip(day_row.select_one('.prob-precip').text)
        })
    return {"today": today_forecast, "ten_day": ten_day_forecast}

def _parse_hourly_forecast(soup):
    hourly_data = {}
    for day_type in ["today", "tomorrow", "dayaftertomorrow"]:
        table = soup.select_one(f'#forecast-point-1h-{day_type}')
        if not table:
            hourly_data[day_type] = []
            continue
        hours_tds = table.select('.hour td')
        data_rows = {
            "weather": [p.text.strip() for p in table.select('.weather td p')],
            "temperature": [td.text.strip() for td in table.select('.temperature td')],
            "prob_precip": [td.text.strip() for td in table.select('.prob-precip td')],
            "precipitation": [td.text.strip() for td in table.select('.precipitation td')],
            "humidity": [td.text.strip() for td in table.select('.humidity td')],
            "wind_direction": [p.text.strip() for p in table.select('.wind-blow td p')],
            "wind_speed": [td.text.strip() for td in table.select('.wind-speed td')],
        }
        day_forecast = []
        for i, hour_td in enumerate(hours_tds):
            try:
                day_forecast.append({
                    "time": int(hour_td.text.strip()),
                    "weather": data_rows["weather"][i],
                    "temperature": _parse_to_number(data_rows["temperature"][i]),
                    "prob_precip": _parse_prob_precip(data_rows["prob_precip"][i]),
                    "precipitation": _parse_to_number(data_rows["precipitation"][i]),
                    "humidity_percent": _parse_to_number(data_rows["humidity"][i]),
                    "wind_direction": data_rows["wind_direction"][i],
                    "wind_speed": _parse_to_number(data_rows["wind_speed"][i]),
                })
            except (IndexError, ValueError):
                _LOGGER.warning(f"Skipping malformed hourly data at index {i} for {day_type}")
                continue
        hourly_data[day_type] = day_forecast
    return hourly_data

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    url_path = entry.data[CONF_URL_PATH]
    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name=DOMAIN,
        update_method=lambda: async_fetch_data(async_get_clientsession(hass), url_path),
        update_interval=timedelta(minutes=30),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
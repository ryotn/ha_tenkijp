"""Config flow for tenki.jp integration."""
import logging
import re
import voluptuous as vol
import aiohttp
from bs4 import BeautifulSoup

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_URL_PATH

_LOGGER = logging.getLogger(__name__)

class TenkiJpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for tenki.jp."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            url_path = user_input[CONF_URL_PATH]
            session = async_get_clientsession(self.hass)
            
            try:
                # URLを検証し、地域名を取得
                url = f"https://tenki.jp{url_path}"
                async with session.get(url) as response:
                    response.raise_for_status()
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # ★★★★★★★★★★ ここからが変更箇所です ★★★★★★★★★★
                    # headタグ内のtitleタグから地域名を取得
                    title_elem = soup.select_one('title')
                    if not title_elem or not title_elem.text:
                        raise ValueError("Title tag not found on page")
                    
                    # タイトルテキストから地域名を抽出
                    # 例: "さいたま市大宮区の今日明日の天気 - ..." -> "さいたま市大宮区"
                    title_text = title_elem.text
                    location_name = title_text.split('の今日明日の天気')[0].strip()

                    if not location_name:
                         raise ValueError("Could not parse location name from title")
                    # ★★★★★★★★★★ ここまでが変更箇所です ★★★★★★★★★★
                    
                    await self.async_set_unique_id(url_path)
                    self._abort_if_unique_id_configured()
                    
                    # ユーザーの希望通りにエンティティ名をフォーマット
                    final_name = f"{location_name} 天気"
                    
                    return self.async_create_entry(
                        title=final_name,
                        data={
                            CONF_URL_PATH: url_path,
                            CONF_NAME: final_name
                        }
                    )
            except aiohttp.ClientError:
                _LOGGER.error("Failed to connect to tenki.jp")
                errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.exception(f"An unexpected error occurred: {e}")
                errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_URL_PATH, default="/forecast/3/14/4310/11103/"
                ): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
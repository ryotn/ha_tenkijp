"""Constants for the tenki.jp integration."""

DOMAIN = "tenkijp"
CONF_URL_PATH = "url_path"

## Mapping of tenki.jp weather text to HA standard states
CONDITION_MAP = {
    "雪": "snowy",
    "雨": "rainy",
    "曇": "cloudy",
    "晴": "sunny",
}
DEFAULT_CONDITION = "sunny"

## 16-point wind bearing map
WIND_BEARING_MAP = {
    "北": 0.0,
    "北北東": 22.5,
    "北東": 45.0,
    "東北東": 67.5,
    "東": 90.0,
    "東南東": 112.5,
    "南東": 135.0,
    "南南東": 157.5,
    "南": 180.0,
    "南南西": 202.5,
    "南西": 225.0,
    "西南西": 247.5,
    "西": 270.0,
    "西北西": 292.5,
    "北西": 315.0,
    "北北西": 337.5,
}
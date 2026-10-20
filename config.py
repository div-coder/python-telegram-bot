import os
from typing import Any, List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    CHANNEL_ID: Union[int, str] = ""
    ADMIN_IDS: Union[str, int, List[Union[int, str]]] = ""
    DATABASE_URL: str = "sqlite+aiosqlite:///quiz_bot.db"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def admin_id_list(self) -> List[int]:
        if isinstance(self.ADMIN_IDS, list):
            return [int(x) for x in self.ADMIN_IDS if str(x).strip().isdigit()]
        if isinstance(self.ADMIN_IDS, int):
            return [self.ADMIN_IDS]
        if isinstance(self.ADMIN_IDS, str):
            cleaned = self.ADMIN_IDS.strip()
            if not cleaned:
                return []
            result = []
            for x in cleaned.split(","):
                part = x.strip()
                if part.isdigit() or (part.startswith("-") and part[1:].isdigit()):
                    result.append(int(part))
            return result
        return []

    @property
    def channel_chat_id(self) -> Union[int, str]:
        if isinstance(self.CHANNEL_ID, int):
            return self.CHANNEL_ID
        try:
            return int(self.CHANNEL_ID)
        except ValueError:
            return self.CHANNEL_ID

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_id_list


settings = Settings()

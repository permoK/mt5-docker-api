from pydantic import BaseSettings, Field, validator
from typing import Optional, List, Dict
import os
from pathlib import Path

class MT5Settings(BaseSettings):
    """Configuración validada para MetaTrader5 Docker"""
    
    # Configuración de Wine
    wine_prefix: str = Field(default="/config/.wine", env="WINEPREFIX")
    wine_version: str = Field(default="win10", env="WINE_VERSION")
    
    # Configuración de MT5
    mt5_port: int = Field(default=8001, gt=1024, lt=65535, env="MT5_PORT")
    mt5_version: str = Field(default="5.0.36", env="MT5_VERSION")
    
    # URLs de descarga
    mono_url: str = Field(
        default="https://dl.winehq.org/wine/wine-mono/8.0.0/wine-mono-8.0.0-x86.msi",
        env="MONO_URL"
    )
    python_url: str = Field(
        default="https://www.python.org/ftp/python/3.9.0/python-3.9.0.exe",
        env="PYTHON_URL"
    )
    mt5_download_url: str = Field(
        default="https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe",
        env="MT5_DOWNLOAD_URL"
    )
    
    # Configuración VNC
    vnc_port: int = Field(default=3000, gt=1024, lt=65535, env="VNC_PORT")
    custom_user: Optional[str] = Field(default=None, env="CUSTOM_USER")
    password: Optional[str] = Field(default=None, env="PASSWORD")
    
    # Python packages
    required_packages: List[str] = Field(
        default=["MetaTrader5==5.0.36", "mt5linux", "pyxdg"],
        env="REQUIRED_PACKAGES"
    )
    
    # Timeouts y reintentos
    download_timeout: int = Field(default=300, gt=0, env="DOWNLOAD_TIMEOUT")
    max_retries: int = Field(default=3, gt=0, env="MAX_RETRIES")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Cache
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    cache_ttl_days: int = Field(default=7, gt=0, env="CACHE_TTL_DAYS")
    
    # Performance
    download_chunk_size: int = Field(default=8192, gt=0, env="DOWNLOAD_CHUNK_SIZE")
    startup_timeout: int = Field(default=300, gt=0, env="STARTUP_TIMEOUT")
    
    @validator('password')
    def password_strength(cls, v):
        if v and len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    @validator('wine_version')
    def validate_wine_version(cls, v):
        allowed = ["win10", "win7", "winxp"]
        if v not in allowed:
            raise ValueError(f'Wine version must be one of {allowed}')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f'Log level must be one of {allowed}')
        return v.upper()
    
    def get_cache_dir(self) -> Path:
        """Obtener directorio de caché"""
        return Path(self.wine_prefix).parent / ".cache"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Instancia global de configuración
settings = MT5Settings()
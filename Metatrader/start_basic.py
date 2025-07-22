#!/usr/bin/env python3
"""
Script mejorado para inicialización de MetaTrader5 con validación Pydantic
"""
import os
import sys
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Agregar el directorio de la app al path
sys.path.append('/app')
from settings import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MT5Installer:
    """Instalador mejorado de MetaTrader5"""
    
    def __init__(self):
        self.settings = settings
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Crear sesión HTTP con reintentos"""
        session = requests.Session()
        retry = Retry(
            total=self.settings.max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def download_file(self, url: str, dest_path: Path) -> bool:
        """Descargar archivo con progreso y validación"""
        try:
            logger.info(f"Descargando {url} a {dest_path}")
            response = self.session.get(
                url, 
                stream=True, 
                timeout=self.settings.download_timeout
            )
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            logger.info(f"Progreso: {progress:.1f}%")
            
            logger.info(f"Descarga completada: {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error descargando {url}: {e}")
            return False
    
    def run_command(self, cmd: list, check: bool = True) -> Optional[subprocess.CompletedProcess]:
        """Ejecutar comando con logging"""
        try:
            logger.info(f"Ejecutando: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=True,
                text=True
            )
            if result.stdout:
                logger.debug(f"STDOUT: {result.stdout}")
            if result.stderr:
                logger.debug(f"STDERR: {result.stderr}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Error ejecutando comando: {e}")
            if check:
                raise
            return None
    
    def install_mono(self):
        """Instalar Wine Mono"""
        mono_path = Path(self.settings.wine_prefix) / "drive_c" / "windows" / "mono"
        
        if mono_path.exists():
            logger.info("Mono ya está instalado")
            return
        
        logger.info("Instalando Wine Mono...")
        mono_installer = Path("/tmp/mono.msi")
        
        if self.download_file(self.settings.mono_url, mono_installer):
            self.run_command([
                "wine", "msiexec", "/i", 
                str(mono_installer), "/qn"
            ], check=False)
            mono_installer.unlink()
            logger.info("Mono instalado correctamente")
    
    def install_mt5(self):
        """Instalar MetaTrader5"""
        mt5_exe = Path(self.settings.wine_prefix) / "drive_c" / "Program Files" / "MetaTrader 5" / "terminal64.exe"
        
        if mt5_exe.exists():
            logger.info("MetaTrader5 ya está instalado")
            return
        
        logger.info("Instalando MetaTrader5...")
        
        # Configurar Wine para Windows 10
        self.run_command([
            "wine", "reg", "add", 
            "HKEY_CURRENT_USER\\Software\\Wine",
            "/v", "Version", "/t", "REG_SZ", 
            "/d", self.settings.wine_version, "/f"
        ])
        
        mt5_installer = Path("/tmp/mt5setup.exe")
        
        if self.download_file(self.settings.mt5_download_url, mt5_installer):
            # Instalar MT5
            process = subprocess.Popen(
                ["wine", str(mt5_installer), "/auto"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Esperar hasta 5 minutos
            try:
                process.wait(timeout=300)
            except subprocess.TimeoutExpired:
                logger.warning("Instalación de MT5 tardando más de lo esperado")
            
            mt5_installer.unlink()
            
            if mt5_exe.exists():
                logger.info("MetaTrader5 instalado correctamente")
            else:
                logger.error("Error instalando MetaTrader5")
    
    def install_python_wine(self):
        """Instalar Python en Wine"""
        try:
            result = self.run_command(["wine", "python", "--version"], check=False)
            if result and result.returncode == 0:
                logger.info(f"Python ya instalado en Wine: {result.stdout}")
                return
        except:
            pass
        
        logger.info("Instalando Python en Wine...")
        python_installer = Path("/tmp/python-installer.exe")
        
        if self.download_file(self.settings.python_url, python_installer):
            self.run_command([
                "wine", str(python_installer),
                "/quiet", "InstallAllUsers=1", "PrependPath=1"
            ], check=False)
            python_installer.unlink()
            
            # Actualizar pip
            self.run_command([
                "wine", "python", "-m", "pip",
                "install", "--upgrade", "pip"
            ], check=False)
    
    def install_python_packages(self):
        """Instalar paquetes Python necesarios"""
        logger.info("Instalando paquetes Python...")
        
        for package in self.settings.required_packages:
            # En Wine
            logger.info(f"Instalando {package} en Wine...")
            self.run_command([
                "wine", "python", "-m", "pip",
                "install", "--no-cache-dir", package
            ], check=False)
            
            # En Linux
            logger.info(f"Instalando {package} en Linux...")
            self.run_command([
                "pip3", "install",
                "--no-cache-dir", package
            ], check=False)
    
    def start_mt5(self):
        """Iniciar MetaTrader5"""
        mt5_exe = Path(self.settings.wine_prefix) / "drive_c" / "Program Files" / "MetaTrader 5" / "terminal64.exe"
        
        if mt5_exe.exists():
            logger.info("Iniciando MetaTrader5...")
            subprocess.Popen(["wine", str(mt5_exe)])
        else:
            logger.error("MetaTrader5 no encontrado")
    
    def start_mt5_server(self):
        """Iniciar servidor mt5linux"""
        logger.info(f"Iniciando servidor mt5linux en puerto {self.settings.mt5_port}...")
        
        subprocess.Popen([
            "python3", "-m", "mt5linux",
            "--host", "0.0.0.0",
            "-p", str(self.settings.mt5_port),
            "-w", "wine", "python.exe"
        ])
        
        # Verificar que el servidor esté funcionando
        time.sleep(5)
        result = self.run_command(["ss", "-tuln"], check=False)
        
        if result and f":{self.settings.mt5_port}" in result.stdout:
            logger.info(f"Servidor mt5linux funcionando en puerto {self.settings.mt5_port}")
        else:
            logger.error("No se pudo verificar el servidor mt5linux")
    
    def run(self):
        """Ejecutar instalación completa"""
        try:
            logger.info("=== Iniciando instalación de MetaTrader5 ===")
            logger.info(f"Configuración: {self.settings.dict()}")
            
            # Crear directorios necesarios
            Path(self.settings.wine_prefix).mkdir(parents=True, exist_ok=True)
            
            # Pasos de instalación
            self.install_mono()
            self.install_mt5()
            self.install_python_wine()
            self.install_python_packages()
            self.start_mt5()
            self.start_mt5_server()
            
            logger.info("=== Instalación completada ===")
            
        except Exception as e:
            logger.error(f"Error durante la instalación: {e}")
            raise

if __name__ == "__main__":
    installer = MT5Installer()
    installer.run()
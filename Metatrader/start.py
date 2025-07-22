#!/usr/bin/env python3
"""
Script mejorado para inicialización de MetaTrader5 con validación Pydantic
Incluye manejo de señales, caché y verificación de integridad
"""
import os
import sys
import subprocess
import time
import logging
import signal
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta

# Agregar el directorio de la app al path
sys.path.append('/app')

try:
    from config import settings
except ImportError:
    # Usar configuración por defecto si no existe config.py
    class DefaultSettings:
        wine_prefix = os.environ.get('WINEPREFIX', '/config/.wine')
        mt5_port = int(os.environ.get('MT5_PORT', '8001'))
        log_level = os.environ.get('LOG_LEVEL', 'INFO')
        max_retries = 3
        download_timeout = 300
        cache_enabled = True
        cache_ttl_days = 7
        mono_url = "https://dl.winehq.org/wine/wine-mono/8.0.0/wine-mono-8.0.0-x86.msi"
        python_url = "https://www.python.org/ftp/python/3.9.0/python-3.9.0.exe"
        mt5_download_url = "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe"
        required_packages = ["MetaTrader5==5.0.36", "mt5linux", "pyxdg"]
        
        def get_cache_dir(self):
            return Path(self.wine_prefix).parent / ".cache"
        
        def dict(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    settings = DefaultSettings()

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper() if hasattr(settings, 'log_level') else 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Checksums conocidos para verificación de integridad
KNOWN_CHECKSUMS = {
    "wine-mono-8.0.0-x86.msi": "3f7b1cd6b7842c09142082e50ece97abe848a033a0838f029c35ce973926c275",
    "python-3.9.0.exe": "fd2e4c52fb5a0f6c0d7f8c31131a21c57b0728d9e8b3ed7c207ceea8f1078918",
}

class GracefulKiller:
    """Maneja señales para shutdown graceful"""
    kill_now = False
    
    def __init__(self):
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        logger.info(f"Señal {signum} recibida. Iniciando shutdown graceful...")
        self.kill_now = True

class MT5Installer:
    """Instalador mejorado de MetaTrader5 con caché y verificación"""
    
    def __init__(self):
        self.settings = settings
        self.session = self._create_session()
        self.cache_dir = Path("/config/.cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.killer = GracefulKiller()
        self.processes = []
        
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
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calcular SHA256 checksum de un archivo"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _verify_checksum(self, file_path: Path, expected_checksum: Optional[str]) -> bool:
        """Verificar integridad del archivo"""
        if not expected_checksum:
            logger.warning(f"No hay checksum conocido para {file_path.name}")
            return True
        
        actual_checksum = self._calculate_checksum(file_path)
        if actual_checksum == expected_checksum:
            logger.info(f"Checksum verificado correctamente para {file_path.name}")
            return True
        else:
            logger.error(f"Checksum incorrecto para {file_path.name}")
            logger.error(f"Esperado: {expected_checksum}")
            logger.error(f"Actual: {actual_checksum}")
            return False
    
    def _get_cache_metadata(self, url: str) -> Dict:
        """Obtener metadata del caché"""
        cache_metadata_file = self.cache_dir / f"{hashlib.md5(url.encode()).hexdigest()}.meta"
        if cache_metadata_file.exists():
            with open(cache_metadata_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_cache_metadata(self, url: str, metadata: Dict):
        """Guardar metadata del caché"""
        cache_metadata_file = self.cache_dir / f"{hashlib.md5(url.encode()).hexdigest()}.meta"
        with open(cache_metadata_file, 'w') as f:
            json.dump(metadata, f)
    
    def download_file(self, url: str, dest_path: Path, expected_checksum: Optional[str] = None) -> bool:
        """Descargar archivo con caché, progreso y validación"""
        try:
            # Verificar si debe terminar
            if self.killer.kill_now:
                return False
            
            # Verificar caché
            cache_file = self.cache_dir / dest_path.name
            cache_metadata = self._get_cache_metadata(url)
            
            # Usar caché si existe y es válido
            if cache_file.exists() and cache_metadata:
                cache_time = datetime.fromisoformat(cache_metadata.get('timestamp', ''))
                if datetime.now() - cache_time < timedelta(days=7):
                    logger.info(f"Usando archivo del caché: {dest_path.name}")
                    cache_file.rename(dest_path)
                    return True
            
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
                    if self.killer.kill_now:
                        logger.info("Descarga interrumpida por señal de terminación")
                        return False
                    
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if downloaded % (1024 * 1024) == 0:  # Log cada MB
                                logger.info(f"Progreso: {progress:.1f}% ({downloaded/1024/1024:.1f}MB/{total_size/1024/1024:.1f}MB)")
            
            # Verificar checksum si está disponible
            filename = dest_path.name
            expected = expected_checksum or KNOWN_CHECKSUMS.get(filename)
            if not self._verify_checksum(dest_path, expected):
                dest_path.unlink()
                return False
            
            # Guardar en caché
            cache_file = self.cache_dir / dest_path.name
            dest_path.link_to(cache_file)
            self._save_cache_metadata(url, {
                'timestamp': datetime.now().isoformat(),
                'checksum': self._calculate_checksum(dest_path)
            })
            
            logger.info(f"Descarga completada: {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error descargando {url}: {e}")
            return False
    
    def run_command(self, cmd: list, check: bool = True, background: bool = False) -> Optional[subprocess.Popen]:
        """Ejecutar comando con logging y manejo de procesos"""
        try:
            if self.killer.kill_now:
                return None
            
            logger.info(f"Ejecutando: {' '.join(cmd)}")
            
            if background:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                self.processes.append(process)
                return process
            else:
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
        if self.killer.kill_now:
            return
        
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
        if self.killer.kill_now:
            return
        
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
            
            # Esperar hasta 5 minutos o hasta señal de terminación
            timeout = 300
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.killer.kill_now:
                    process.terminate()
                    return
                
                if process.poll() is not None:
                    break
                
                time.sleep(1)
            
            if process.poll() is None:
                logger.warning("Instalación de MT5 tardando más de lo esperado")
                process.terminate()
            
            mt5_installer.unlink()
            
            if mt5_exe.exists():
                logger.info("MetaTrader5 instalado correctamente")
            else:
                logger.error("Error instalando MetaTrader5")
    
    def install_python_wine(self):
        """Instalar Python en Wine"""
        if self.killer.kill_now:
            return
        
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
        if self.killer.kill_now:
            return
        
        logger.info("Instalando paquetes Python...")
        
        for package in self.settings.required_packages:
            if self.killer.kill_now:
                return
            
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
        if self.killer.kill_now:
            return
        
        mt5_exe = Path(self.settings.wine_prefix) / "drive_c" / "Program Files" / "MetaTrader 5" / "terminal64.exe"
        
        if mt5_exe.exists():
            logger.info("Iniciando MetaTrader5...")
            self.run_command(["wine", str(mt5_exe)], background=True)
        else:
            logger.error("MetaTrader5 no encontrado")
    
    def start_mt5_server(self):
        """Iniciar servidor mt5linux"""
        if self.killer.kill_now:
            return
        
        logger.info(f"Iniciando servidor mt5linux en puerto {self.settings.mt5_port}...")
        
        self.run_command([
            "python3", "-m", "mt5linux",
            "--host", "0.0.0.0",
            "-p", str(self.settings.mt5_port),
            "-w", "wine", "python.exe"
        ], background=True)
        
        # Verificar que el servidor esté funcionando
        time.sleep(5)
        result = self.run_command(["ss", "-tuln"], check=False)
        
        if result and f":{self.settings.mt5_port}" in result.stdout:
            logger.info(f"Servidor mt5linux funcionando en puerto {self.settings.mt5_port}")
        else:
            logger.error("No se pudo verificar el servidor mt5linux")
    
    def cleanup(self):
        """Limpiar procesos al terminar"""
        logger.info("Limpiando procesos...")
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
    
    def run(self):
        """Ejecutar instalación completa"""
        try:
            logger.info("=== Iniciando instalación de MetaTrader5 ===")
            logger.info(f"Configuración: {self.settings.dict()}")
            
            # Crear directorios necesarios
            Path(self.settings.wine_prefix).mkdir(parents=True, exist_ok=True)
            
            # Pasos de instalación
            steps = [
                self.install_mono,
                self.install_mt5,
                self.install_python_wine,
                self.install_python_packages,
                self.start_mt5,
                self.start_mt5_server
            ]
            
            for step in steps:
                if self.killer.kill_now:
                    logger.info("Instalación interrumpida por señal de terminación")
                    break
                step()
            
            if not self.killer.kill_now:
                logger.info("=== Instalación completada ===")
                
                # Mantener el proceso vivo
                while not self.killer.kill_now:
                    time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error durante la instalación: {e}")
            raise
        finally:
            self.cleanup()
            logger.info("Script terminado")

if __name__ == "__main__":
    installer = MT5Installer()
    installer.run()
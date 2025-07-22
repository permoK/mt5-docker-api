#!/usr/bin/env python3
"""
Script de validación completo para MT5 Docker API
"""
import sys
import time
import requests
import subprocess
import json
from datetime import datetime

class Validator:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.vnc_url = "http://localhost:3000"
        self.errors = []
        self.warnings = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def check_port(self, port, service):
        """Verificar si un puerto está abierto"""
        try:
            result = subprocess.run(
                ["nc", "-zv", "localhost", str(port)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.log(f"✓ Puerto {port} ({service}) está abierto")
                return True
            else:
                self.log(f"✗ Puerto {port} ({service}) no está accesible", "ERROR")
                self.errors.append(f"Puerto {port} ({service}) no accesible")
                return False
        except Exception as e:
            self.log(f"✗ Error verificando puerto {port}: {e}", "ERROR")
            self.errors.append(f"Error verificando puerto {port}")
            return False
    
    def check_vnc(self):
        """Verificar acceso VNC"""
        self.log("Verificando acceso VNC...")
        try:
            response = requests.get(self.vnc_url, timeout=10)
            if response.status_code == 200:
                self.log("✓ VNC web interface accesible")
                return True
            else:
                self.log(f"✗ VNC devolvió código {response.status_code}", "ERROR")
                self.errors.append(f"VNC status code: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"✗ Error accediendo a VNC: {e}", "ERROR")
            self.errors.append(f"VNC error: {str(e)}")
            return False
    
    def check_api_health(self):
        """Verificar health endpoint de la API"""
        self.log("Verificando API health...")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log("✓ API está saludable")
                    if data.get("mt5_connected"):
                        self.log("✓ MT5 está conectado")
                    else:
                        self.log("⚠ MT5 no está conectado", "WARNING")
                        self.warnings.append("MT5 no conectado")
                    return True
                else:
                    self.log("✗ API reporta estado no saludable", "ERROR")
                    self.errors.append("API unhealthy")
                    return False
            else:
                self.log(f"✗ API health devolvió código {response.status_code}", "ERROR")
                self.errors.append(f"API health status: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"✗ Error accediendo a API health: {e}", "ERROR")
            self.errors.append(f"API health error: {str(e)}")
            return False
    
    def check_api_docs(self):
        """Verificar documentación de la API"""
        self.log("Verificando documentación API...")
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=10)
            if response.status_code == 200:
                self.log("✓ Documentación API accesible")
                return True
            else:
                self.log(f"✗ Docs devolvió código {response.status_code}", "ERROR")
                self.errors.append(f"API docs status: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"✗ Error accediendo a docs: {e}", "ERROR")
            self.errors.append(f"API docs error: {str(e)}")
            return False
    
    def check_api_endpoints(self):
        """Verificar endpoints principales de la API"""
        endpoints = [
            ("/symbols", "GET", None),
            ("/account", "GET", None),
            ("/positions", "GET", None),
        ]
        
        self.log("Verificando endpoints de la API...")
        all_ok = True
        
        for endpoint, method, data in endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                elif method == "POST":
                    response = requests.post(
                        f"{self.base_url}{endpoint}", 
                        json=data, 
                        timeout=10
                    )
                
                if response.status_code in [200, 404]:  # 404 is OK for empty data
                    self.log(f"✓ {method} {endpoint} - OK ({response.status_code})")
                else:
                    self.log(f"✗ {method} {endpoint} - Error ({response.status_code})", "ERROR")
                    self.errors.append(f"{method} {endpoint}: {response.status_code}")
                    all_ok = False
                    
            except Exception as e:
                self.log(f"✗ {method} {endpoint} - Error: {e}", "ERROR")
                self.errors.append(f"{method} {endpoint}: {str(e)}")
                all_ok = False
        
        return all_ok
    
    def check_websocket(self):
        """Verificar WebSocket endpoint"""
        self.log("Verificando WebSocket...")
        try:
            import websocket
            
            ws = websocket.WebSocket()
            ws.connect("ws://localhost:8000/ws/ticks/EURUSD", timeout=5)
            
            # Esperar un mensaje
            ws.settimeout(5)
            try:
                message = ws.recv()
                data = json.loads(message)
                if "symbol" in data:
                    self.log("✓ WebSocket funcional")
                    ws.close()
                    return True
            except websocket.WebSocketTimeoutException:
                self.log("⚠ WebSocket conectado pero sin datos", "WARNING")
                self.warnings.append("WebSocket sin datos")
                ws.close()
                return True
                
        except ImportError:
            self.log("⚠ Módulo websocket no instalado, saltando prueba", "WARNING")
            self.warnings.append("WebSocket no probado")
            return True
        except Exception as e:
            self.log(f"✗ Error en WebSocket: {e}", "ERROR")
            self.errors.append(f"WebSocket error: {str(e)}")
            return False
    
    def run_all_checks(self):
        """Ejecutar todas las validaciones"""
        self.log("=== Iniciando validación completa ===")
        
        # Esperar a que los servicios inicien
        self.log("Esperando 10 segundos para que los servicios inicien...")
        time.sleep(10)
        
        # Verificar puertos
        ports_ok = all([
            self.check_port(3000, "VNC"),
            self.check_port(8000, "API"),
            self.check_port(8001, "MT5")
        ])
        
        if not ports_ok:
            self.log("Algunos puertos no están disponibles", "WARNING")
        
        # Verificar servicios
        self.check_vnc()
        self.check_api_health()
        self.check_api_docs()
        self.check_api_endpoints()
        self.check_websocket()
        
        # Resumen
        self.log("=== Resumen de validación ===")
        
        if self.errors:
            self.log(f"Errores encontrados: {len(self.errors)}", "ERROR")
            for error in self.errors:
                self.log(f"  - {error}", "ERROR")
        
        if self.warnings:
            self.log(f"Advertencias: {len(self.warnings)}", "WARNING")
            for warning in self.warnings:
                self.log(f"  - {warning}", "WARNING")
        
        if not self.errors:
            self.log("✓ Todas las validaciones pasaron exitosamente!", "SUCCESS")
            return 0
        else:
            self.log("✗ Se encontraron errores en la validación", "ERROR")
            return 1

if __name__ == "__main__":
    validator = Validator()
    sys.exit(validator.run_all_checks())
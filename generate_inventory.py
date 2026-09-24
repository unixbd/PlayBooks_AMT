#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
Script de Automatización de Inventario AMT para Ansible / AWX
===============================================================================
Descripción:
    Este script consume el endpoint de Power Automate que entrega el inventario
    de servidores AMT en formato JSON, gestiona los reintentos y el flujo
    asíncrono (HTTP 202 con cabecera Location / Retry-After), y genera un archivo
    de inventario en formato .ini 100% compatible con Ansible y AWX.

Características:
    - Sin dependencias externas (usa la biblioteca estándar de Python: urllib, json).
    - Manejo robusto de patrón asíncrono Power Automate (202 Accepted + Location polling).
    - Reintentos automáticos con backoff en caso de error 502 (upstream server timeout).
    - Detección automática y flexible de campos JSON (hostname, ip, sistema operativo).
    - Agrupación estricta en [linux_servers] y [windows_servers] con variables de transporte WinRM.
    - Soporte de ejecución offline mediante archivo JSON (--input-json).
===============================================================================
"""

import sys
import os
import json
import time
import argparse
import logging
import re
import urllib.request
import urllib.error

# Configuración por defecto del endpoint
DEFAULT_URL = (
    "https://fa8b912a65384981a8828b261d2010.26.environment.api.powerplatform.com:443"
    "/powerautomate/automations/direct/cu/11/workflows/0a2790d39da24543bc13574d21c5199d"
    "/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0"
    "&sig=S5sEZpOppk_8u3gAxIPI5QVR1dDJxAqBtT1FFAaIk_g"
)
DEFAULT_TOKEN = "6685485248785safdasf%#57866"
DEFAULT_OUTPUT_FILE = "inventory_amt.ini"
DEFAULT_MAX_RETRIES = 15
DEFAULT_RETRY_DELAY = 20
DEFAULT_POLL_TIMEOUT = 120
DEFAULT_POLL_INTERVAL = 5


def setup_logger(verbose: bool = False):
    """Configura el formato del logging en consola."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def fetch_inventory_from_api(
    url: str = DEFAULT_URL,
    token: str = DEFAULT_TOKEN,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: int = DEFAULT_RETRY_DELAY,
    poll_timeout: int = DEFAULT_POLL_TIMEOUT,
    poll_interval: int = DEFAULT_POLL_INTERVAL
) -> any:
    """
    Realiza la petición al endpoint de Power Automate con lógica de reintentos
    y soporte de polling asíncrono (HTTP 202).
    """
    headers = {
        "token-middleware": token,
        "Accept": "application/json",
        "User-Agent": "AWX-AMT-Inventory-Fetcher/1.0"
    }

    for attempt in range(1, max_retries + 1):
        logging.info("Intento %d de %d: Conectando a Power Automate...", attempt, max_retries)
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=45) as resp:
                status_code = resp.getcode()
                resp_headers = dict(resp.info())
                logging.info("Respuesta inicial HTTP: %d", status_code)

                # Si responde 200 OK directamente
                if status_code == 200:
                    raw_data = resp.read().decode("utf-8")
                    return json.loads(raw_data)

        except urllib.error.HTTPError as e:
            status_code = e.code
            resp_headers = dict(e.headers)
            logging.info("Respuesta HTTP: %d (%s)", status_code, e.reason)

            # Manejo de flujo asíncrono (202 Accepted)
            if status_code == 202:
                location = resp_headers.get("Location") or resp_headers.get("location")
                retry_after_str = resp_headers.get("Retry-After") or resp_headers.get("retry-after")
                
                try:
                    wait_time = int(retry_after_str) if retry_after_str else 10
                except ValueError:
                    wait_time = 10

                if location:
                    logging.info("Operación asíncrona en curso. Esperando %d s antes de consultar Location...", wait_time)
                    time.sleep(wait_time)

                    # Polling del Location URL
                    poll_start = time.time()
                    while (time.time() - poll_start) < poll_timeout:
                        logging.debug("Consultando Location: %s", location)
                        try:
                            loc_req = urllib.request.Request(location, method="GET")
                            with urllib.request.urlopen(loc_req, timeout=30) as loc_resp:
                                if loc_resp.getcode() == 200:
                                    raw_data = loc_resp.read().decode("utf-8")
                                    logging.info("¡Datos obtenidos exitosamente desde Location!")
                                    return json.loads(raw_data)
                        except urllib.error.HTTPError as loc_err:
                            if loc_err.code == 202:
                                logging.debug("Flujo aún en ejecución (202). Esperando %d s...", poll_interval)
                                time.sleep(poll_interval)
                                continue
                            elif loc_err.code == 502:
                                logging.warning("El upstream server no respondió a tiempo (502). Reintentando ciclo completo...")
                                break
                            else:
                                logging.error("Error en Location HTTP %d: %s", loc_err.code, loc_err.reason)
                                break
                        except Exception as poll_ex:
                            logging.warning("Error consultando Location: %s", poll_ex)
                            break
                else:
                    logging.warning("Recibido 202 pero sin cabecera Location.")

            elif status_code == 502:
                logging.warning("El servidor upstream de Power Automate respondió 502 Bad Gateway.")
            else:
                logging.warning("Error HTTP inesperado %d: %s", status_code, e.reason)

        except urllib.error.URLError as e:
            logging.warning("Error de conexión de red: %s", e.reason)
        except Exception as e:
            logging.warning("Excepción durante la petición: %s", e)

        if attempt < max_retries:
            logging.info("Esperando %d segundos antes del siguiente reintento...", retry_delay)
            time.sleep(retry_delay)

    raise TimeoutError(f"No fue posible obtener el inventario tras {max_retries} intentos.")


def extract_servers_list(data: any) -> list:
    """
    Localiza la lista de servidores dentro de la respuesta JSON,
    manejando diferentes formatos comunes devueltos por Power Automate.
    """
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        # Claves comunes donde Power Automate o APIs encapsulan listas
        for key in ["value", "data", "servidores", "servers", "hosts", "items", "rows", "inventario"]:
            if key in data and isinstance(data[key], list):
                return data[key]

        # Si el dict tiene una sola clave que es una lista
        for val in data.values():
            if isinstance(val, list):
                return val

    raise ValueError("No se pudo identificar una lista de servidores en el JSON recibido.")


def parse_server_entry(entry: dict) -> dict:
    """
    Extrae de forma tolerante y flexible:
    - hostname
    - ip / ansible_host
    - so / os (windows vs linux)
    """
    # Normalizar claves a minúsculas
    norm = {str(k).lower().strip(): v for k, v in entry.items() if v is not None}

    # 1. Detectar Hostname
    hostname = None
    for k in ["hostname", "host", "nombre", "server", "servidor", "name", "computername", "equipo"]:
        if k in norm and norm[k]:
            hostname = str(norm[k]).strip()
            break

    # 2. Detectar IP
    ip = None
    for k in ["ip", "ip_address", "ipaddress", "ansible_host", "direccion_ip", "host_ip"]:
        if k in norm and norm[k]:
            ip = str(norm[k]).strip()
            break

    # Si no hay hostname pero sí IP
    if not hostname and ip:
        hostname = ip

    # Si no hay IP pero el hostname parece una IP
    if hostname and not ip:
        ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        if re.match(ip_pattern, hostname):
            ip = hostname

    # 3. Detectar Sistema Operativo
    os_val = ""
    for k in ["so", "os", "sistema_operativo", "operating_system", "tipo", "platform", "tipo_so", "os_name"]:
        if k in norm and norm[k]:
            os_val = str(norm[k]).lower().strip()
            break

    # Clasificar Windows vs Linux
    is_windows = False
    if "win" in os_val:
        is_windows = True
    elif any(term in os_val for term in ["linux", "redhat", "rhel", "centos", "unix", "ubuntu", "suse", "aix", "solaris"]):
        is_windows = False
    else:
        # Heurística sobre el hostname si el campo de SO no fue concluyente
        if hostname and ("win" in hostname.lower()):
            is_windows = True
        else:
            is_windows = False

    return {
        "hostname": hostname or "unknown-host",
        "ip": ip,
        "is_windows": is_windows,
        "raw": entry
    }


def generate_ini_inventory(servers: list) -> str:
    """
    Construye el contenido en formato .ini para AWX con los grupos solicitados:
    [linux_servers]
    [windows_servers]
    [windows_servers:vars]
    """
    linux_list = []
    windows_list = []

    for item in servers:
        if not isinstance(item, dict):
            continue
        parsed = parse_server_entry(item)
        line = parsed["hostname"]
        if parsed["ip"]:
            line += f" ansible_host={parsed['ip']}"

        if parsed["is_windows"]:
            windows_list.append(line)
        else:
            linux_list.append(line)

    # Ordenar alfabéticamente para estabilidad en git/AWX
    linux_list.sort()
    windows_list.sort()

    lines = [
        "# ==============================================================================",
        "# Inventario AMT generado automáticamente para AWX / Ansible",
        f"# Fecha de generación: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"# Total Servidores: {len(linux_list) + len(windows_list)} (Linux: {len(linux_list)}, Windows: {len(windows_list)})",
        "# ==============================================================================",
        "",
        "[linux_servers]"
    ]
    lines.extend(linux_list if linux_list else ["# (Sin servidores Linux registrados)"])

    lines.extend([
        "",
        "[windows_servers]"
    ])
    lines.extend(windows_list if windows_list else ["# (Sin servidores Windows registrados)"])

    lines.extend([
        "",
        "# Solo se declaran parámetros de transporte, nada de contraseñas ni llaves",
        "[windows_servers:vars]",
        "ansible_connection=winrm",
        "ansible_winrm_server_cert_validation=ignore",
        "ansible_winrm_transport=ntlm   # o kerberos / credssp",
        ""
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generador de Inventario AMT para AWX desde Power Automate"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="URL del endpoint de Power Automate"
    )
    parser.add_argument(
        "--token",
        default=DEFAULT_TOKEN,
        help="Token de cabecera token-middleware"
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT_FILE,
        help=f"Ruta del archivo de inventario .ini a generar (defecto: {DEFAULT_OUTPUT_FILE})"
    )
    parser.add_argument(
        "--input-json", "-i",
        help="Ruta a un archivo JSON local existente (modo offline sin llamar a la API)"
    )
    parser.add_argument(
        "--save-json",
        default="amt_inventory_raw.json",
        help="Ruta donde guardar una copia del JSON crudo recibido para auditoría/caché"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f"Número máximo de reintentos sobre el endpoint (defecto: {DEFAULT_MAX_RETRIES})"
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=DEFAULT_RETRY_DELAY,
        help=f"Segundos de espera entre reintentos cuando el endpoint falla (defecto: {DEFAULT_RETRY_DELAY}s)"
    )
    parser.add_argument(
        "--poll-timeout",
        type=int,
        default=120,
        help="Tiempo máximo en segundos para el polling asíncrono del Location (defecto: 120s)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Activar modo detallado de depuración (DEBUG)"
    )

    args = parser.parse_args()
    setup_logger(args.verbose)

    logging.info("=== Iniciando Generación de Inventario AMT para AWX ===")

    # 1. Obtención de datos JSON
    if args.input_json:
        logging.info("Modo local: Leyendo archivo JSON desde '%s'...", args.input_json)
        with open(args.input_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        try:
            data = fetch_inventory_from_api(
                url=args.url,
                token=args.token,
                max_retries=args.max_retries,
                retry_delay=args.retry_delay,
                poll_timeout=args.poll_timeout
            )
            # Guardar copia del JSON descargado
            if args.save_json:
                with open(args.save_json, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                logging.info("Copia de seguridad del JSON guardada en '%s'.", args.save_json)
        except Exception as e:
            logging.error("Error fatal obteniendo datos de la API: %s", e)
            sys.exit(1)

    # 2. Extracción y análisis de servidores
    try:
        servers = extract_servers_list(data)
        logging.info("Se encontraron %d registros en la data de inventario.", len(servers))
    except Exception as e:
        logging.error("Error analizando estructura de servidores: %s", e)
        sys.exit(1)

    # 3. Generación del archivo .ini
    ini_content = generate_ini_inventory(servers)

    output_path = os.path.abspath(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ini_content)

    logging.info("¡Inventario AWX generado exitosamente en: %s!", output_path)
    print("\n" + "=" * 40 + " CONTENIDO GENERADO " + "=" * 40)
    print(ini_content)
    print("=" * 100)


if __name__ == "__main__":
    main()

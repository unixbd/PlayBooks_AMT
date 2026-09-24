#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
Script de Automatización de Inventario AMT para Ansible / AWX
===============================================================================
Basado en el estándar de actualización de inventarios de Unix (PlayBooks_Unix).
Descarga los datos del inventario AMT desde Power Automate, genera el archivo
.ini compatible con AWX (separando linux_servers y windows_servers con WinRM),
y sincroniza los cambios automáticamente con el repositorio Git.
===============================================================================
"""

import requests
import time
import json
import re
import unicodedata
import subprocess
from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, Union

# Configuración por defecto
URL_DEFAULT = (
    "https://fa8b912a65384981a8828b261d2010.26.environment.api.powerplatform.com:443"
    "/powerautomate/automations/direct/cu/11/workflows/0a2790d39da24543bc13574d21c5199d"
    "/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0"
    "&sig=S5sEZpOppk_8u3gAxIPI5QVR1dDJxAqBtT1FFAaIk_g"
)

HEADERS_DEFAULT = {
    'token-middleware': '6685485248785safdasf%#57866',
    'Accept': 'application/json',
    'User-Agent': 'AWX-AMT-Inventory/1.0'
}

MAX_RETRIES = 15
RETRY_DELAY = 20
POLL_TIMEOUT = 120
POLL_INTERVAL = 5


def limpiar_cliente(cliente):
    if not cliente:
        return "Sin_Cliente"
    cliente = unicodedata.normalize('NFKD', cliente).encode('ASCII', 'ignore').decode('ASCII')
    cliente = cliente.replace('-', '_')
    cliente = re.sub(r'[^\w]', '', cliente)
    return cliente


def limpiar_hostname(hostname):
    if not hostname:
        return "Sin_Hostname"
    return hostname.replace(' ', '').strip()


def obtener_primera_ip(ip_str):
    if not ip_str:
        return "Sin_IP"
    ip_match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', str(ip_str))
    return ip_match.group(0) if ip_match else "Sin_IP"


def _sp_value(x: Any) -> str:
    """Normaliza valores provenientes de SharePoint / Power Automate."""
    if isinstance(x, dict):
        return str(x.get("Value", "") or "")
    if x is None:
        return ""
    return str(x).strip()


def cargar_json_raw(ruta):
    """Carga archivo JSON con soporte para UTF-8 y UTF-8 con BOM."""
    for enc in ("utf-8", "utf-8-sig"):
        try:
            with open(ruta, "r", encoding=enc) as f:
                return json.load(f)
        except UnicodeDecodeError:
            pass
        except json.JSONDecodeError:
            try:
                with open(ruta, "r", encoding=enc) as f:
                    return [json.loads(line) for line in f if line.strip()]
            except Exception:
                pass
    raise ValueError(f"No se pudo decodificar el archivo {ruta}")


def actualizar_repo():
    """Actualiza el repositorio Git local antes de descargar contenido."""
    try:
        subprocess.run(["git", "pull", "--rebase"], check=True)
        print("Se actualizo el repositorio Local con GIT")
    except subprocess.CalledProcessError as e:
        print(f"Error al actualizar el repositorio Git: {e}")


def subir_cambios_repo(archivos, mensaje="Actualizacion automatica del inventario AMT"):
    """
    Actualiza el repositorio Git:
    - Agrega archivos al staging area.
    - Si hay cambios, hace commit, pull --rebase y push.
    - Si no hay cambios, informa y termina.
    """
    try:
        subprocess.run(["git", "add"] + archivos, check=True)

        status_check = subprocess.run(
            ["git", "status", "--porcelain"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if not status_check.stdout.strip():
            print("No hay cambios para commit.")
            return

        subprocess.run(["git", "commit", "-m", mensaje], check=False)
        subprocess.run(["git", "pull", "--rebase"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Cambios actualizados en el repositorio Git.")

    except subprocess.CalledProcessError as e:
        print(f"\nError al actualizar el repositorio Git: {e}")


def generate_inventario_json(url, headers, filename="inventario_amt.json", max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
    """
    Consume el endpoint de Power Automate gestionando el patrón asíncrono (202),
    polling del Location y reintentos automáticos en caso de timeout del upstream (502).
    """
    for intento in range(1, max_retries + 1):
        print(f"[{intento}/{max_retries}] Iniciando solicitud a Power Automate...")
        try:
            response = requests.get(url, headers=headers, timeout=45)
            print(f"Respuesta inicial HTTP: {response.status_code}")

            if response.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(response.content)
                print(f"Archivo JSON descargado exitosamente como '{filename}'.")
                return True

            elif response.status_code == 202:
                print("Proceso iniciado en Power Automate (202 Accepted).")
                location_url = response.headers.get('location') or response.headers.get('Location')

                if location_url:
                    retry_after = response.headers.get('Retry-After') or response.headers.get('retry-after')
                    wait_initial = int(retry_after) if retry_after and retry_after.isdigit() else 10
                    print(f"Esperando {wait_initial}s para consulta de estado...")
                    time.sleep(wait_initial)

                    start_poll = time.time()
                    while (time.time() - start_poll) < POLL_TIMEOUT:
                        try:
                            status_resp = requests.get(location_url, headers=headers, timeout=30)
                            if status_resp.status_code == 200:
                                with open(filename, "wb") as f:
                                    f.write(status_resp.content)
                                print(f"Archivo JSON descargado exitosamente como '{filename}'.")
                                return True
                            elif status_resp.status_code == 202:
                                print(f"Flujo en ejecucion (202). Esperando {POLL_INTERVAL}s...")
                                time.sleep(POLL_INTERVAL)
                            elif status_resp.status_code == 502:
                                print("Upstream server respondio 502 Bad Gateway. Reintentando flujo completo...")
                                break
                            else:
                                print(f"Respuesta inesperada en location: {status_resp.status_code}")
                                break
                        except Exception as poll_err:
                            print(f"Error consultando Location: {poll_err}")
                            break
                else:
                    print("No se encontro cabecera Location en respuesta 202.")
            elif response.status_code == 502:
                print("Servidor upstream de Power Automate retorno 502.")
            else:
                print(f"Codigo de respuesta inesperado: {response.status_code}")

        except Exception as req_err:
            print(f"Error en peticion HTTP: {req_err}")

        if intento < max_retries:
            print(f"Esperando {retry_delay}s antes del siguiente reintento...")
            time.sleep(retry_delay)

    raise TimeoutError(f"No fue posible descargar el inventario tras {max_retries} intentos.")


def extraer_lista_servidores(data: Any) -> list:
    """Extrae la lista de servidores del JSON tolerando múltiples estructuras."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ["value", "data", "servidores", "servers", "hosts", "items"]:
            if key in data and isinstance(data[key], list):
                return data[key]
        for val in data.values():
            if isinstance(val, list):
                return val
    return []


def clasificar_so(item: dict) -> Tuple[str, str, bool]:
    """
    Retorna (hostname, ip, is_windows) a partir del item del JSON.
    """
    # Mapeo flexible
    norm = {str(k).lower().strip(): _sp_value(v) for k, v in item.items()}

    # Hostname
    hostname = None
    for k in ["cod_hostname", "hostname", "host", "nombre", "server", "servidor", "name", "computername", "equipo"]:
        if k in norm and norm[k]:
            hostname = limpiar_hostname(norm[k])
            break

    # IP
    ip = None
    for k in ["ip_x002d_mgmt", "ip", "ip_address", "ipaddress", "ansible_host", "direccion_ip", "host_ip"]:
        if k in norm and norm[k]:
            ip = obtener_primera_ip(norm[k])
            break

    if not hostname and ip:
        hostname = ip
    if hostname and not ip:
        ip_candidata = obtener_primera_ip(hostname)
        if ip_candidata != "Sin_IP":
            ip = ip_candidata

    # SO
    so_val = ""
    for k in ["so", "os", "sistema_operativo", "operating_system", "tipo", "platform", "tipo_so"]:
        if k in norm and norm[k]:
            so_val = norm[k].lower()
            break

    is_windows = False
    if "win" in so_val:
        is_windows = True
    elif any(term in so_val for term in ["linux", "redhat", "rhel", "centos", "unix", "ubuntu", "suse", "aix", "solaris"]):
        is_windows = False
    else:
        if hostname and ("win" in hostname.lower()):
            is_windows = True

    return (hostname or "Sin_Hostname", ip or "Sin_IP", is_windows)


def guardar_inventario_amt_ini(servidores: list, filename="INVENTARIO_AMT.ini"):
    """
    Genera el archivo .ini para AWX con los grupos requeridos:
    [linux_servers]
    [windows_servers]
    [windows_servers:vars]
    """
    linux_list = []
    windows_list = []
    omitidos = 0

    for item in servidores:
        if not isinstance(item, dict):
            continue
        hostname, ip, is_windows = clasificar_so(item)

        if hostname == "Sin_Hostname":
            omitidos += 1
            continue

        line = hostname
        if ip and ip != "Sin_IP":
            line += f" ansible_host={ip}"

        if is_windows:
            windows_list.append(line)
        else:
            linux_list.append(line)

    linux_list = sorted(set(linux_list))
    windows_list = sorted(set(windows_list))

    with open(filename, "w", encoding="utf-8") as f:
        f.write("# ==============================================================================\n")
        f.write("# Inventario AMT generado automáticamente para AWX / Ansible\n")
        f.write(f"# Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total: {len(linux_list) + len(windows_list)} (Linux: {len(linux_list)}, Windows: {len(windows_list)})\n")
        f.write("# ==============================================================================\n\n")

        f.write("[linux_servers]\n")
        if linux_list:
            for h in linux_list:
                f.write(f"{h}\n")
        else:
            f.write("# (Sin servidores Linux registrados)\n")
        f.write("\n")

        f.write("[windows_servers]\n")
        if windows_list:
            for h in windows_list:
                f.write(f"{h}\n")
        else:
            f.write("# (Sin servidores Windows registrados)\n")
        f.write("\n")

        f.write("# Solo se declaran parámetros de transporte, nada de contraseñas ni llaves\n")
        f.write("[windows_servers:vars]\n")
        f.write("ansible_connection=winrm\n")
        f.write("ansible_winrm_server_cert_validation=ignore\n")
        f.write("ansible_winrm_transport=ntlm   # o kerberos / credssp\n")

    print(f"Proceso {filename}. Linux: {len(linux_list)}, Windows: {len(windows_list)}, Omitidos: {omitidos}")


if __name__ == '__main__':
    use_git = True
    refresh_inv = True

    # 1. Actualizar repositorio Git
    if use_git:
        actualizar_repo()

    # 2. Descargar inventario JSON desde Power Automate
    if refresh_inv:
        try:
            generate_inventario_json(URL_DEFAULT, HEADERS_DEFAULT, filename="inventario_amt.json")
        except Exception as e:
            print(f"Aviso: {e}")

    # 3. Cargar JSON descargado (o muestra local de respaldo)
    json_path = "inventario_amt.json"
    try:
        inventario_raw = cargar_json_raw(json_path)
        print(f"JSON '{json_path}' cargado OK.")
    except Exception as e:
        print(f"Error cargando {json_path}: {e}. Intentando sample_amt_inventory.json...")
        try:
            inventario_raw = cargar_json_raw("sample_amt_inventory.json")
        except Exception as ex2:
            print(f"Error fatal: {ex2}")
            exit(1)

    servidores = extraer_lista_servidores(inventario_raw)
    print(f"Total registros detectados: {len(servidores)}")

    # 4. Generar archivo de inventario .ini para AWX
    guardar_inventario_amt_ini(servidores, filename="INVENTARIO_AMT.ini")

    # 5. Sincronizar y subir cambios al repositorio Git
    archivos = ["inventario_amt.json", "INVENTARIO_AMT.ini"]
    if use_git:
        subir_cambios_repo(archivos)

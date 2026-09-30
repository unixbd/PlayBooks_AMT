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

import os
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
    cliente = unicodedata.normalize('NFKD', str(cliente)).encode('ASCII', 'ignore').decode('ASCII')
    cliente = cliente.strip().replace(' ', '_').replace('-', '_')
    cliente = re.sub(r'[^\w_]', '', cliente)
    return cliente or "Sin_Cliente"


def limpiar_cod_serv(cod):
    if not cod:
        return ""
    return str(cod).strip().replace(' ', '').replace('\n', '').replace('\r', '')


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
    - Agrega archivos existentes al staging area.
    - Si hay cambios, hace commit, pull --rebase y push.
    - Si no hay cambios, informa y termina.
    """
    try:
        archivos_existentes = [a for a in archivos if os.path.exists(a)]
        if not archivos_existentes:
            print("No se encontraron archivos para agregar al commit.")
            return

        subprocess.run(["git", "add"] + archivos_existentes, check=True)

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
                    consecutive_502 = 0
                    while (time.time() - start_poll) < POLL_TIMEOUT:
                        try:
                            status_resp = requests.get(location_url, headers={'Accept': 'application/json'}, timeout=30)
                            if status_resp.status_code == 200:
                                with open(filename, "wb") as f:
                                    f.write(status_resp.content)
                                print(f"Archivo JSON descargado exitosamente como '{filename}'.")
                                return True
                            elif status_resp.status_code == 202:
                                consecutive_502 = 0
                                print(f"Flujo en ejecucion (202). Esperando {POLL_INTERVAL}s...")
                                time.sleep(POLL_INTERVAL)
                            elif status_resp.status_code == 502:
                                consecutive_502 += 1
                                print(f"Upstream server respondio 502 Bad Gateway (intento {consecutive_502}/5).")
                                if consecutive_502 >= 5:
                                    print("Demasiados 502 en polling. Reiniciando flujo completo...")
                                    break
                                time.sleep(5)
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


def clasificar_so(item: dict) -> Tuple[str, str, str, str, bool]:
    """
    Retorna (cliente, cod_serv, hostname, ip, is_windows) a partir del item del JSON de AMT SharePoint.
    Descarta equipos marcados como INACTIVO.
    """
    norm = {str(k).lower().strip(): _sp_value(v) for k, v in item.items()}

    # Estado: si está explícitamente inactivo, descartar
    for st_key in ["field_18", "estado", "status", "state"]:
        if st_key in norm and norm[st_key].upper() == "INACTIVO":
            return ("Sin_Cliente", "Sin_CodServ", "Sin_Hostname", "Sin_IP", False)

    # Cliente (field_0 es el campo en SharePoint AMT)
    cliente = "Sin_Cliente"
    for k in ["field_0", "cliente", "client", "customer", "empresa"]:
        if k in norm and norm[k]:
            candidato_cli = limpiar_cliente(norm[k])
            if candidato_cli != "Sin_Cliente":
                cliente = candidato_cli
                break

    # COD-SERV (field_4 es el campo de código de servidor en SharePoint AMT)
    cod_serv = None
    for k in ["field_4", "cod_serv", "cod_servidor", "codigo_servidor", "codigo", "cod"]:
        if k in norm and norm[k]:
            candidato_cod = limpiar_cod_serv(norm[k])
            if candidato_cod:
                cod_serv = candidato_cod
                break

    # Hostname (field_3 es el nombre de servidor en SharePoint AMT)
    hostname = None
    for k in ["field_3", "cod_hostname", "hostname", "host", "nombre", "server", "servidor", "name", "computername", "equipo"]:
        if k in norm and norm[k]:
            candidato_host = limpiar_hostname(norm[k])
            if candidato_host and candidato_host != "Sin_Hostname":
                hostname = candidato_host
                break

    # Fallback si no tiene cod_serv pero sí hostname
    if not cod_serv and hostname:
        cod_serv = hostname

    # IP (field_7 es IP-GESTION, field_6 es respaldo/alterna, field_5 es IP-PRODUCCION)
    ip = None
    for k in ["field_7", "ip_gestion", "ip_mgmt", "ip_x002d_mgmt", "field_6", "field_5", "ip", "ip_address", "ipaddress", "ansible_host", "direccion_ip", "host_ip"]:
        if k in norm and norm[k]:
            candidata = obtener_primera_ip(norm[k])
            if candidata != "Sin_IP":
                ip = candidata
                break

    # SO: TIPO_SO (UNIX / WINDOWS)
    so_val = ""
    for k in ["tipo_so", "so", "os", "sistema_operativo", "operating_system", "tipo", "platform"]:
        if k in norm and norm[k]:
            so_val = norm[k].lower()
            break

    is_windows = False
    if "win" in so_val:
        is_windows = True
    elif any(term in so_val for term in ["linux", "redhat", "rhel", "centos", "unix", "ubuntu", "suse", "aix", "solaris"]):
        is_windows = False
    else:
        if (hostname and "win" in hostname.lower()) or (cod_serv and "win" in cod_serv.lower()):
            is_windows = True

    return (cliente, cod_serv or "Sin_CodServ", hostname or "Sin_Hostname", ip or "Sin_IP", is_windows)


def guardar_inventario_amt_ini(servidores: list, filename="INVENTARIO_AMT.ini"):
    """
    Genera el archivo .ini para AWX con:
    1. Registro único de COD-SERV por cada Cliente ([PREVISORA], [PCCAS], etc.)
    2. Grupos globales de SO ([linux_servers], [windows_servers]) con COD-SERV únicos
    3. Variables WinRM para Windows ([windows_servers:vars])
    """
    # Mapeo: cliente -> dict(cod_serv -> info) para garantizar unicidad por cliente
    clientes_dict = defaultdict(dict)
    linux_set = set()
    windows_set = set()
    omitidos = 0

    for item in servidores:
        if not isinstance(item, dict):
            continue
        cliente, cod_serv, hostname, ip, is_windows = clasificar_so(item)

        if cod_serv == "Sin_CodServ":
            omitidos += 1
            continue

        if cod_serv not in clientes_dict[cliente]:
            clientes_dict[cliente][cod_serv] = {
                "ip": ip,
                "hostname": hostname,
                "is_windows": is_windows
            }
        else:
            # Si no tenía IP válida y este registro sí la tiene, la actualizamos
            if clientes_dict[cliente][cod_serv]["ip"] == "Sin_IP" and ip != "Sin_IP":
                clientes_dict[cliente][cod_serv]["ip"] = ip

        if is_windows:
            windows_set.add(cod_serv)
        else:
            linux_set.add(cod_serv)

    linux_list = sorted(linux_set)
    windows_list = sorted(windows_set)
    total_unicos = len(linux_list) + len(windows_list)

    # Mapa global de IP por cod_serv
    host_ip_map = {}
    for cli in clientes_dict:
        for cod, info in clientes_dict[cli].items():
            if info["ip"] and info["ip"] != "Sin_IP":
                host_ip_map[cod] = info["ip"]

    with open(filename, "w", encoding="utf-8") as f:
        f.write("# ==============================================================================\n")
        f.write("# Inventario AMT generado automáticamente para AWX / Ansible\n")
        f.write("# Identificador principal: COD-SERV (Registro único por servidor)\n")
        f.write(f"# Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total: {total_unicos} servidores únicos (Linux: {len(linux_list)}, Windows: {len(windows_list)}) en {len(clientes_dict)} Clientes\n")
        f.write("# ==============================================================================\n\n")

        # 1. Secciones por cada Cliente (con COD-SERV único)
        f.write("# ==============================================================================\n")
        f.write("# 1. GRUPOS POR CLIENTE (COD-SERV único)\n")
        f.write("# ==============================================================================\n\n")
        for cli in sorted(clientes_dict.keys()):
            f.write(f"[{cli}]\n")
            for cod in sorted(clientes_dict[cli].keys()):
                ip = clientes_dict[cli][cod]["ip"]
                line = cod
                if ip and ip != "Sin_IP":
                    line += f" ansible_host={ip}"
                f.write(f"{line}\n")
            f.write("\n")

        # 2. Grupos por Sistema Operativo
        f.write("# ==============================================================================\n")
        f.write("# 2. GRUPOS POR SISTEMA OPERATIVO (COD-SERV único)\n")
        f.write("# ==============================================================================\n\n")
        f.write("[linux_servers]\n")
        if linux_list:
            for cod in linux_list:
                ip = host_ip_map.get(cod, "")
                line = cod + (f" ansible_host={ip}" if ip and ip != "Sin_IP" else "")
                f.write(f"{line}\n")
        else:
            f.write("# (Sin servidores Linux registrados)\n")
        f.write("\n")

        f.write("[windows_servers]\n")
        if windows_list:
            for cod in windows_list:
                ip = host_ip_map.get(cod, "")
                line = cod + (f" ansible_host={ip}" if ip and ip != "Sin_IP" else "")
                f.write(f"{line}\n")
        else:
            f.write("# (Sin servidores Windows registrados)\n")
        f.write("\n")

        # 3. Variables de conexión Windows (WinRM)
        f.write("# ==============================================================================\n")
        f.write("# 3. VARIABLES DE TRANSPORTE WINDOWS (WinRM)\n")
        f.write("# ==============================================================================\n")
        f.write("[windows_servers:vars]\n")
        f.write("ansible_connection=winrm\n")
        f.write("ansible_winrm_server_cert_validation=ignore\n")
        f.write("ansible_winrm_transport=ntlm   # o kerberos / credssp\n")

    print(f"Archivo '{filename}' escrito exitosamente.")
    print(f"Total: {total_unicos} servidores COD-SERV únicos en {len(clientes_dict)} clientes. Omitidos: {omitidos}")


if __name__ == '__main__':
    use_git = True
    refresh_inv = True

    # 1. Actualizar repositorio Git
    if use_git:
        actualizar_repo()

    # 2. Descargar inventario JSON desde Power Automate
    json_path = "inventario_amt.json"
    descarga_exitosa = False

    if refresh_inv:
        try:
            descarga_exitosa = generate_inventario_json(URL_DEFAULT, HEADERS_DEFAULT, filename=json_path)
        except Exception as e:
            print(f"\nAviso: {e}")

    # Si no se pudo descargar y el archivo no existe, finalizar limpiamente sin tocar Git
    if not os.path.exists(json_path):
        print(f"\n[ALERTA] No se pudo descargar '{json_path}' desde Power Automate.")
        print("El servicio upstream de Power Automate devolvió error 502 (NoResponse).")
        print("Esto indica que el origen de datos interno (middleware / base de datos / gateway) no está respondiendo en este momento.")
        print("El script finaliza sin alterar el repositorio Git.")
        exit(1)

    # 3. Cargar JSON descargado
    try:
        inventario_raw = cargar_json_raw(json_path)
        print(f"JSON '{json_path}' cargado OK.")
    except Exception as e:
        print(f"Error fatal cargando {json_path}: {e}")
        exit(1)

    servidores = extraer_lista_servidores(inventario_raw)
    print(f"Total registros detectados: {len(servidores)}")

    # 4. Generar archivo de inventario .ini para AWX
    ini_path = "INVENTARIO_AMT.ini"
    guardar_inventario_amt_ini(servidores, filename=ini_path)

    # 5. Sincronizar y subir cambios al repositorio Git
    archivos = [json_path, ini_path]
    if use_git:
        subir_cambios_repo(archivos)

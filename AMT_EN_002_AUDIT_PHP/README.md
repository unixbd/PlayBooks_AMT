# AMT_EN_002_AUDIT_PHP

## Auditoría Automatizada de Vulnerabilidad Crítica en PHP (CERT-EU 2026-018)

Este proyecto automatiza la auditoría e inventario de versiones de **PHP** en la infraestructura de servidores de **AMT (Linux y Windows)**, evaluando la exposición frente al boletín oficial de seguridad **[CERT-EU 2026-018](https://cert.europa.eu/publications/security-advisories/2026-018/)**.

---

### 1. Resumen de la Vulnerabilidad

El boletín **CERT-EU 2026-018** reporta dos vulnerabilidades críticas de **Ejecución Remota de Código (RCE)** sin autenticación:

* **CVE-2026-109618 (GHSA-w8hw-w9fx-j79w) - CVSS 9.2:** Corrupción de memoria durante la gestión de excepciones de memoria insuficiente (*Out of Memory - OOM*) provocada por `memory_limit` mediante `longjmp()`.
* **CVE-2026-109619 (GHSA-6wmf-4rv5-p3rp) - CVSS 9.2:** Uso de estado global obsoleto (*Stale Global State*) que sobrevive a errores fatales de peticiones anteriores en procesos de trabajo (PHP-FPM, Apache mod_php, etc.).

#### Versiones Afectadas y Parches Oficiales

| Rama PHP | Versiones Vulnerables | Versión Segura (Con Parche) | Estado |
| :--- | :--- | :--- | :--- |
| **PHP 8.5** | Versiones anteriores a 8.5.12 | **>= 8.5.12** | Parche Oficial Disponible |
| **PHP 8.4** | Versiones anteriores a 8.4.27 | **>= 8.4.27** | Parche Oficial Disponible |
| **PHP 8.3** | Versiones anteriores a 8.3.36 | **>= 8.3.36** | Parche Oficial Disponible |
| **PHP 8.2** | Versiones anteriores a 8.2.35 | **>= 8.2.35** | Parche Oficial Disponible |
| **PHP <= 8.1** | Todas (8.1, 8.0, 7.x, 5.x) | N/A (Descontinuadas por PHP) | **CRÍTICO - Fin de ciclo de vida (EOL)** |

---

### 2. Estructura del Proyecto

```text
PlayBooks_AMT/
├── AMT_EN_002_AUDIT_PHP/
│   ├── audit_vulnerabilidad_php.yml   # Playbook principal de auditoría
│   ├── email_template.j2              # Plantilla Jinja2 de correo HTML con métricas y tabla
│   └── README.md                      # Documentación del proyecto
└── resources/
    ├── img/
    │   └── FirmaClaro.gif             # Firma institucional
    └── templates/
        └── mail/
            ├── header.html            # Encabezado estándar institucional
            └── footer.html            # Pie de correo institucional y avisos legales
```

---

### 3. Criterios de Evaluación por Servidor

| Condición Detectada | Estado en Reporte | Badge / Indicador | Dictamen / Acción |
| :--- | :--- | :--- | :--- |
| Sin binario de PHP | `NO_APLICA` | `NO APLICA` (Gris) | Servidor sin PHP instalado. Sin riesgo para esta vulnerabilidad. |
| Versión PHP con parche aplicado | `NO_VULNERABLE` | `NO VULNERABLE` (Verde) | Cumple con la versión mínima segura indicada por CERT-EU 2026-018. |
| PHP 8.2 a 8.5 sin parche | `VULNERABLE` | `VULNERABLE` (Rojo) | Expuesto a CVE-2026-109618 / CVE-2026-109619. Requiere actualización inmediata. |
| PHP rama EOL (<= 8.1) | `VULNERABLE` | `VULNERABLE` (Rojo) | Versión descontinuada sin soporte oficial. Requiere migración de versión mayor. |
| Falla SSH o WinRM | `SIN_CONEXION` | `SIN CONEXIÓN` (Naranja) | Error de conectividad al intentar evaluar el servidor. |

---

### 4. Variables de Ejecución en AWX / Ansible

El playbook puede ejecutarse directamente o parametrizarse mediante **Extra Vars** en AWX:

| Variable | Tipo | Valor por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `target_hosts` | String | `'all'` | Grupo o lista de servidores a auditar. |
| `email_smtp_host` | String | `'172.22.88.6'` | Servidor de retransmisión SMTP institucional. |
| `email_smtp_port` | Entero | `25` | Puerto SMTP. |
| `email_remitente` | String | `'amt@telmexla.net.co'` | Dirección de correo del remitente. |
| `email_destinatarios` | String | `'middletierdatacente@claro.com.co'` | Destinatarios principales del reporte. |
| `email_copia` | String | `''` | Destinatarios en copia (CC). |
| `email_asunto` | String | `'Reporte de Auditoría - Vulnerabilidad Crítica PHP (CERT-EU 2026-018)'` | Asunto del correo. |
| `enviar_correo` | Booleano | `true` | Permite activar o desactivar el envío del correo. |
| `connect_timeout` | Entero | `10` | Timeout de conexión SSH / WinRM en segundos. |

#### Ejemplo de Extra Vars en AWX:

```yaml
---
target_hosts: "linux_servers"
email_destinatarios: "seguridad_amt@claro.com.co"
email_copia: "operaciones_middleware@claro.com.co"
enviar_correo: true
```

---

### 5. Características del Reporte por Correo

* **Diseño Institucional:** Integra encabezado (`header.html`) y pie de página (`footer.html`) oficiales de Claro/AMT con aviso de confidencialidad legal y metadatos de Job ID, fecha y hora.
* **Resumen Ejecutivo (KPIs):** Bloques con conteo total de servidores evaluados, vulnerables (alerta), seguros, no aplicables y sin conexión.
* **Cuadro Detallado de Servidores:**
  1. **Nombre de la Máquina:** Hostname e IP de gestión.
  2. **Versión de SO:** Distribución Linux detectada (`/etc/os-release`, `redhat-release`) o Windows Server (PowerShell / CIM).
  3. **Versión PHP:** Versión detectada (`php -v`) o "No instalado".
  4. **¿Es Vulnerable?:** Badge visual de clasificación según los umbrales de CERT-EU 2026-018.
  5. **Dictamen / Acción:** Recomendación específica de mitigación o actualización.

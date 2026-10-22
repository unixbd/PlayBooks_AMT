/**
 * Tipos e interfaces centrados en SERVICIOS, DOMINIOS E INSTANCIAS DE CAPA MEDIA (SERV-MANEJADO)
 */

export interface SharePointExpandedValue {
  '@odata.type'?: string;
  Id?: number;
  Value?: string;
}

export type SharePointField<T = string> = SharePointExpandedValue | T | null | undefined;

/**
 * Representa la estructura cruda entregada por Power Automate desde SharePoint
 */
export interface RawSharePointItem {
  ItemInternalId?: string;
  ID?: number;
  Title?: string;
  field_0?: SharePointField<string>;  // Cliente (ej. PCCAS, PREVISORA, AVVILLAS)
  field_1?: SharePointField<string>;  // Ambiente (PRODUCCION, PRUEBAS, CONTINGENCIA)
  field_2?: SharePointField<string>;  // Tipo de Servicio (SERV. MANEJADO, HOST)
  field_3?: string;                   // Hostname
  field_4?: string;                   // COD-SERV (Identificador de host)
  field_5?: string;                   // IP Producción
  field_6?: string;                   // IP Backup / Respaldo
  field_7?: string;                   // IP Gestión (ansible_host)
  field_8?: string;                   // Plataforma / Middleware (TOMCAT, WEBLOGIC, APACHE, JBOSS, IIS)
  field_9?: string;                   // Directorio Home / Binarios de la instancia
  field_10?: SharePointField<string>; // Tipo Aplicación
  field_11?: string;                  // Versión de la Aplicación
  field_12?: string;                  // Usuario SO de ejecución (root, tomcat, etc.)
  field_13?: string | number;         // Puerto de Servicio (PTO-SERVICIO)
  field_14?: string | number;         // Puerto Administrativo (PTO-ADMON)
  field_15?: string;                  // URL de Administración (URL-ADMON)
  field_16?: string;                  // Ruta de Logs de la instancia (LOGS)
  field_17?: string;                  // Instancia / Manejado / Dominio (SERV-MANEJADO)
  field_18?: SharePointField<string>; // Estado (ACTIVO / INACTIVO)
  field_19?: string;                  // Observaciones / Historial PAM
  TIPO_SO?: SharePointField<string>;  // UNIX / WINDOWS
  DATACENTER?: SharePointField<string>; // TRIARA / ORTEZAL
  ServidorFisico?: string;            // Blade / Hipervisor físico
  MONITOREO?: string;                 // URL SiteScope / Monitoreo
  PYTHON_INTERPRETER?: string;        // Intérprete Python opcional
  [key: string]: any;
}

export type HealthStatus = 'OK' | 'WARNING' | 'CRITICAL';
export type OSType = 'LINUX' | 'WINDOWS' | 'UNKNOWN';

export type PlatformCategory =
  | 'TOMCAT'
  | 'WEBLOGIC'
  | 'APACHE'
  | 'JBOSS'
  | 'IIS'
  | 'DOCKER'
  | 'CASSANDRA'
  | 'GENESYS'
  | 'OTRO';

/**
 * Entidad principal del Dashboard: Instancia de Servicio / Dominio de Capa Media
 */
export interface ServiceInstance {
  id: string;                         // Identificador único (ej. TFM1285_139_TOMCAT)
  service_name: string;               // Nombre principal del Servicio / Manejado (SERV-MANEJADO)
  instance_raw: string;               // Valor crudo de field_17
  platform: string;                   // Plataforma descriptiva (ej. "Apache Tomcat 8.5")
  platform_category: PlatformCategory;// Categoría normalizada para filtros
  app_version: string;                // Versión de la aplicación middleware
  service_type: string;               // SERV. MANEJADO, HOST, etc.

  // Puertos y Endpoints del servicio
  service_port: number | null;        // PTO-SERVICIO (ej. 8080)
  admin_port: number | null;          // PTO-ADMON (ej. 443 o 8443)
  expected_ports: number[];           // Lista de puertos esperados [pto_servicio, pto_admin]
  admin_url: string;                  // URL-ADMON canónica
  logs_path: string;                  // Ruta absoluta de logs de la instancia
  home_path: string;                  // Directorio home de ejecución
  execution_user: string;             // Usuario del SO que ejecuta el proceso (root, tomcat)

  // Atributos del Nodo Anfitrión (Host Machine)
  cod_serv: string;                   // Código del servidor anfitrión (ej. TFM1285)
  hostname: string;                   // Hostname anfitrión
  ip_gestion: string;                 // IP de Gestión (ansible_host)
  ip_produccion?: string;             // IP de Producción
  ip_backup?: string;                 // IP de Respaldo
  os_type: OSType;                    // LINUX o WINDOWS
  datacenter: string;                 // TRIARA, ORTEZAL, etc.
  physical_host?: string;             // Servidor físico blade/hipervisor
  python_interpreter?: string;        // Intérprete Python configurado en el nodo

  // Clasificación de Negocio
  client: string;                     // Cliente normalizado (ej. ATH, AVVILLAS, PCCAS)
  environment: string;                // PRODUCCION, PRUEBAS, CONTINGENCIA

  // Estado de Salud enfocado en Disponibilidad del Servicio
  status: HealthStatus;               // OK, WARNING, CRITICAL
  status_reason: string;              // Diagnóstico de salud de la instancia
  http_code?: number;                 // Código HTTP simulado (200, 503, 504, etc.)
  monitoring_url?: string;            // URL de SiteScope / monitoreo externo
  notes?: string;                     // Observaciones PAM / historial
  is_active: boolean;                 // true si está ACTIVO en inventario
}

export interface PlatformKPI {
  platform: PlatformCategory;
  count: number;
}

export interface ClientKPI {
  client: string;
  totalServices: number;
  healthy: number;
  warning: number;
  critical: number;
  uniqueHosts: number;
}

export interface DashboardKPIs {
  totalServices: number;
  healthyServices: number;
  warningServices: number;
  criticalServices: number;
  totalUniqueHosts: number;
  linuxServices: number;
  windowsServices: number;
  productionServices: number;
  testServices: number;
  contingencyServices: number;
  platformBreakdown: PlatformKPI[];
  clientBreakdown: ClientKPI[];
}

export interface ServiceInventoryData {
  summary: DashboardKPIs;
  services: ServiceInstance[];
  clients: string[];
  platforms: PlatformCategory[];
  rawCount: number;
  activeCount: number;
}

import React, { useState, useMemo } from 'react';
import { RawSharePointItem, ServiceInstance, HealthStatus, PlatformCategory } from '../types/inventory';
import { transformInventory } from '../utils/inventoryAdapter';

export interface ServiceDashboardProps {
  rawInventory?: RawSharePointItem[];
}

export const ServerDashboard: React.FC<ServiceDashboardProps> = ({ rawInventory = [] }) => {
  // Transforma el inventario crudo al modelo centrado en servicios e instancias
  const inventoryData = useMemo(() => {
    return transformInventory(rawInventory);
  }, [rawInventory]);

  // Estados para filtros y búsqueda
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedClient, setSelectedClient] = useState<string>('ALL');
  const [selectedPlatform, setSelectedPlatform] = useState<string>('ALL');
  const [selectedEnvironment, setSelectedEnvironment] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [selectedOS, setSelectedOS] = useState<string>('ALL');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [copiedItem, setCopiedItem] = useState<string | null>(null);

  // Copiado al portapapeles
  const handleCopy = (text: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopiedItem(text);
    setTimeout(() => setCopiedItem(null), 2000);
  };

  // Filtrado de servicios
  const filteredServices = useMemo(() => {
    return inventoryData.services.filter((svc) => {
      // Búsqueda por texto (Servicio, COD-SERV, Hostname, IP, Puertos)
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase().trim();
        const matchesName = svc.service_name.toLowerCase().includes(query);
        const matchesCod = svc.cod_serv.toLowerCase().includes(query);
        const matchesHost = svc.hostname.toLowerCase().includes(query);
        const matchesIp = svc.ip_gestion.toLowerCase().includes(query);
        const matchesPlat = svc.platform.toLowerCase().includes(query);
        const matchesPort = svc.expected_ports.some((p) => String(p).includes(query));

        if (!matchesName && !matchesCod && !matchesHost && !matchesIp && !matchesPlat && !matchesPort) {
          return false;
        }
      }

      // Filtro de Cliente
      if (selectedClient !== 'ALL' && svc.client !== selectedClient) {
        return false;
      }

      // Filtro de Plataforma
      if (selectedPlatform !== 'ALL' && svc.platform_category !== selectedPlatform) {
        return false;
      }

      // Filtro de Ambiente
      if (selectedEnvironment !== 'ALL') {
        if (!svc.environment.includes(selectedEnvironment)) return false;
      }

      // Filtro de Estado de Salud
      if (selectedStatus !== 'ALL' && svc.status !== selectedStatus) {
        return false;
      }

      // Filtro de Sistema Operativo del Host
      if (selectedOS !== 'ALL' && svc.os_type !== selectedOS) {
        return false;
      }

      return true;
    });
  }, [inventoryData.services, searchTerm, selectedClient, selectedPlatform, selectedEnvironment, selectedStatus, selectedOS]);

  const { summary } = inventoryData;

  // Estilos de badge por plataforma
  const getPlatformBadge = (plat: PlatformCategory) => {
    switch (plat) {
      case 'TOMCAT':
        return 'bg-amber-500/10 text-amber-300 border-amber-500/30';
      case 'WEBLOGIC':
        return 'bg-purple-500/10 text-purple-300 border-purple-500/30';
      case 'APACHE':
        return 'bg-red-500/10 text-red-300 border-red-500/30';
      case 'JBOSS':
        return 'bg-rose-500/10 text-rose-300 border-rose-500/30';
      case 'IIS':
        return 'bg-blue-500/10 text-blue-300 border-blue-500/30';
      case 'DOCKER':
        return 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30';
      case 'CASSANDRA':
        return 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30';
      default:
        return 'bg-slate-500/10 text-slate-300 border-slate-500/30';
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-6 lg:p-8 font-sans">
      {/* Encabezado */}
      <header className="mb-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 rounded-xl text-indigo-400 shadow-inner">
              <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                <span>Supervisión de Capa Media AMT</span>
                <span className="text-xs font-mono font-normal px-2 py-0.5 rounded bg-indigo-900/50 text-indigo-300 border border-indigo-700/50">
                  SERV-MANEJADO
                </span>
              </h1>
              <p className="text-xs sm:text-sm text-slate-400">
                Monitoreo individual de instancias, dominios, puertos y URLs administrativas
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm">
              <span className="w-2 h-2 mr-2 bg-emerald-400 rounded-full animate-pulse"></span>
              {summary.totalServices} Servicios en {summary.totalUniqueHosts} Servidores
            </span>
          </div>
        </div>
      </header>

      {/* Tarjetas KPI de Servicios */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Total Servicios */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Instancias / Manejados</span>
            <span className="text-xs font-mono text-indigo-400">{summary.totalUniqueHosts} hosts físicos/VM</span>
          </div>
          <div className="flex items-baseline justify-between">
            <div className="text-3xl font-extrabold text-white">{summary.totalServices}</div>
            <div className="text-xs text-slate-400 flex gap-1.5 font-mono">
              <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                🐧 {summary.linuxServices}
              </span>
              <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                🪟 {summary.windowsServices}
              </span>
            </div>
          </div>
          <div className="mt-3 text-xs text-slate-400">
            Distribuidos en <strong className="text-slate-200">{summary.clientBreakdown.length}</strong> clientes corporativos.
          </div>
        </div>

        {/* Servicios OK */}
        <div className="bg-slate-900/80 border border-emerald-950/60 rounded-xl p-5 shadow-lg backdrop-blur">
          <div className="flex items-center justify-between text-emerald-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Disponibilidad OK</span>
            <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="flex items-baseline justify-between">
            <div className="text-3xl font-extrabold text-emerald-400">{summary.healthyServices}</div>
            <span className="text-xs font-semibold text-emerald-500 bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-900/60">
              {summary.totalServices > 0 ? Math.round((summary.healthyServices / summary.totalServices) * 100) : 0}% En Línea
            </span>
          </div>
          <div className="mt-3 text-xs text-slate-400">
            Puertos de servicio respondiendo y URL-ADMON HTTP 200.
          </div>
        </div>

        {/* Advertencias */}
        <div className="bg-slate-900/80 border border-amber-950/60 rounded-xl p-5 shadow-lg backdrop-blur">
          <div className="flex items-center justify-between text-amber-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Advertencias</span>
            <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div className="flex items-baseline justify-between">
            <div className="text-3xl font-extrabold text-amber-400">{summary.warningServices}</div>
            <span className="text-xs font-medium text-amber-500">Requiere Atención</span>
          </div>
          <div className="mt-3 text-xs text-slate-400">
            Latencia alta, redirección o puertos no especificados.
          </div>
        </div>

        {/* Críticos */}
        <div className="bg-slate-900/80 border border-rose-950/60 rounded-xl p-5 shadow-lg backdrop-blur">
          <div className="flex items-center justify-between text-rose-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Instancias Críticas</span>
            <svg className="w-4 h-4 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="flex items-baseline justify-between">
            <div className="text-3xl font-extrabold text-rose-400">{summary.criticalServices}</div>
            <span className="text-xs font-medium text-rose-500">Caído / Inaccesible</span>
          </div>
          <div className="mt-3 text-xs text-slate-400">
            Puerto cerrado, timeout HTTP o host sin conectividad.
          </div>
        </div>
      </section>

      {/* Filtros Rápidos por Plataforma (Chips) */}
      <section className="mb-4 overflow-x-auto pb-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-2">Plataformas:</span>
          <button
            onClick={() => setSelectedPlatform('ALL')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              selectedPlatform === 'ALL'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/20'
                : 'bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-white border border-slate-800'
            }`}
          >
            Todas ({summary.totalServices})
          </button>
          {summary.platformBreakdown.map((item) => (
            <button
              key={item.platform}
              onClick={() => setSelectedPlatform(item.platform)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all flex items-center gap-1.5 border ${
                selectedPlatform === item.platform
                  ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-500/20'
                  : 'bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-white border-slate-800'
              }`}
            >
              <span>{item.platform}</span>
              <span className="px-1.5 py-0.2 rounded text-[10px] bg-slate-800 text-slate-300 font-mono">
                {item.count}
              </span>
            </button>
          ))}
        </div>
      </section>

      {/* Barra de Filtros y Búsqueda */}
      <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 mb-6 backdrop-blur">
        <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {/* Buscador de Servicio / Host */}
          <div className="md:col-span-2 lg:col-span-2 relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar por Servicio, COD-SERV, Host, IP o Puerto..."
              className="w-full pl-9 pr-8 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-slate-500 hover:text-slate-300"
              >
                ✕
              </button>
            )}
          </div>

          {/* Filtro por Cliente */}
          <div>
            <select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">Todos los Clientes ({inventoryData.clients.length})</option>
              {inventoryData.clients.map((cli) => (
                <option key={cli} value={cli}>
                  {cli}
                </option>
              ))}
            </select>
          </div>

          {/* Filtro por Ambiente */}
          <div>
            <select
              value={selectedEnvironment}
              onChange={(e) => setSelectedEnvironment(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">Todos los Ambientes</option>
              <option value="PROD">Producción</option>
              <option value="PRUEB">Pruebas / QA</option>
              <option value="CONTING">Contingencia</option>
            </select>
          </div>

          {/* Filtro por Estado de Salud */}
          <div>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">Todos los Estados</option>
              <option value="OK">OK (Saludable)</option>
              <option value="WARNING">Advertencia</option>
              <option value="CRITICAL">Crítico</option>
            </select>
          </div>

          {/* Contador de Servicios Filtrados */}
          <div className="flex items-center justify-end text-xs text-slate-400 font-mono">
            {filteredServices.length} de {summary.totalServices} instancias
          </div>
        </div>
      </section>

      {/* Tabla Principal: Service-Centric */}
      <section className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/80 text-slate-400 font-semibold text-xs uppercase tracking-wider">
                <th className="py-3.5 px-4">Servicio / Manejado</th>
                <th className="py-3.5 px-4">Nodo Anfitrión (Host)</th>
                <th className="py-3.5 px-4">Cliente / Entorno</th>
                <th className="py-3.5 px-4 text-center">Puertos (Srv / Adm)</th>
                <th className="py-3.5 px-4">Consola & Logs</th>
                <th className="py-3.5 px-4 text-center">Disponibilidad</th>
                <th className="py-3.5 px-4 text-center">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-normal">
              {filteredServices.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    No se encontraron servicios que coincidan con los criterios de búsqueda.
                  </td>
                </tr>
              ) : (
                filteredServices.map((svc) => {
                  const isExpanded = expandedId === svc.id;

                  return (
                    <React.Fragment key={svc.id}>
                      <tr
                        onClick={() => setExpandedId(isExpanded ? null : svc.id)}
                        className={`hover:bg-slate-800/50 cursor-pointer transition-colors ${
                          isExpanded ? 'bg-slate-800/30' : ''
                        }`}
                      >
                        {/* 1. Servicio / Manejado */}
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-white text-base tracking-tight hover:text-indigo-400 transition-colors">
                              {svc.service_name}
                            </span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-semibold tracking-wide border ${getPlatformBadge(svc.platform_category)}`}>
                              {svc.platform_category}
                            </span>
                          </div>
                          <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                            {svc.appVersion && (
                              <span className="text-slate-400 font-mono">v{svc.appVersion}</span>
                            )}
                            <span className="text-slate-500">•</span>
                            <span className="text-slate-500 italic text-[11px] truncate max-w-[200px]" title={svc.instance_raw}>
                              {svc.instance_raw || svc.service_type}
                            </span>
                          </div>
                        </td>

                        {/* 2. Nodo Anfitrión */}
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-1.5 font-semibold text-slate-200">
                            <span className="font-mono text-indigo-300">{svc.cod_serv}</span>
                            <span className="text-slate-600">/</span>
                            <span className="text-xs text-slate-300 font-mono truncate max-w-[150px]" title={svc.hostname}>
                              {svc.hostname}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 mt-0.5 text-xs">
                            <span className="font-mono text-slate-400">{svc.ip_gestion}</span>
                            <button
                              onClick={(e) => handleCopy(svc.ip_gestion, e)}
                              className="text-slate-500 hover:text-slate-300 p-0.5"
                              title="Copiar IP de Gestión"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                              </svg>
                            </button>
                            {copiedItem === svc.ip_gestion && (
                              <span className="text-[10px] text-emerald-400 font-mono">¡Copiado!</span>
                            )}
                            <span className="text-[11px] text-slate-500 ml-1">
                              {svc.os_type === 'LINUX' ? '🐧 Linux' : '🪟 Windows'} ({svc.datacenter})
                            </span>
                          </div>
                        </td>

                        {/* 3. Cliente / Ambiente */}
                        <td className="py-3.5 px-4">
                          <div className="font-medium text-slate-200">{svc.client}</div>
                          <span className={`inline-block mt-0.5 px-2 py-0.5 rounded text-[10px] font-semibold tracking-wide border ${
                            svc.environment.includes('PROD')
                              ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                              : svc.environment.includes('CONTING')
                              ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                              : 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                          }`}>
                            {svc.environment}
                          </span>
                        </td>

                        {/* 4. Puertos Específicos */}
                        <td className="py-3.5 px-4 text-center">
                          <div className="inline-flex items-center gap-1.5">
                            {svc.service_port ? (
                              <span className="px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-300 font-mono text-xs border border-indigo-800/60" title="Puerto de Servicio">
                                S: {svc.service_port}
                              </span>
                            ) : (
                              <span className="text-xs text-slate-500 font-mono">S: -</span>
                            )}

                            {svc.admin_port ? (
                              <span className="px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 font-mono text-xs border border-amber-800/60" title="Puerto Administrativo">
                                A: {svc.admin_port}
                              </span>
                            ) : (
                              <span className="text-xs text-slate-500 font-mono">A: -</span>
                            )}
                          </div>
                        </td>

                        {/* 5. Consola & Logs */}
                        <td className="py-3.5 px-4">
                          {svc.admin_url ? (
                            <a
                              href={svc.admin_url.startsWith('http') ? svc.admin_url : `http://${svc.admin_url}`}
                              target="_blank"
                              rel="noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 underline font-mono"
                            >
                              <span>Consola Admin</span>
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                            </a>
                          ) : (
                            <span className="text-xs text-slate-500">Sin URL admin</span>
                          )}

                          {svc.logs_path && (
                            <div className="text-[11px] text-slate-400 font-mono truncate max-w-[180px] mt-0.5" title={svc.logs_path}>
                              📂 {svc.logs_path}
                            </div>
                          )}
                        </td>

                        {/* 6. Disponibilidad (Salud) */}
                        <td className="py-3.5 px-4 text-center">
                          <span
                            className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                              svc.status === 'OK'
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : svc.status === 'WARNING'
                                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            }`}
                            title={svc.status_reason}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                              svc.status === 'OK' ? 'bg-emerald-400' : svc.status === 'WARNING' ? 'bg-amber-400' : 'bg-rose-400'
                            }`}></span>
                            {svc.status}
                          </span>
                          <div className="text-[10px] text-slate-500 mt-0.5 font-mono">
                            User: {svc.execution_user}
                          </div>
                        </td>

                        {/* 7. Expansión */}
                        <td className="py-3.5 px-4 text-center">
                          <button
                            className="p-1 rounded hover:bg-slate-700 text-slate-400"
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedId(isExpanded ? null : svc.id);
                            }}
                          >
                            <svg
                              className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </button>
                        </td>
                      </tr>

                      {/* Ficha Técnica Expandida del Servicio */}
                      {isExpanded && (
                        <tr className="bg-slate-950/80 border-b border-slate-800">
                          <td colSpan={7} className="p-4 sm:p-6">
                            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-inner">
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 mb-4 border-b border-slate-800">
                                <div>
                                  <h4 className="font-bold text-white text-base flex items-center gap-2">
                                    <span>Ficha Técnica: {svc.service_name}</span>
                                    <span className="text-xs font-mono font-normal text-indigo-400">
                                      ({svc.platform} en {svc.cod_serv})
                                    </span>
                                  </h4>
                                  <p className="text-xs text-slate-400 mt-0.5">
                                    Diagnóstico de disponibilidad: <span className="text-slate-200 font-medium">{svc.status_reason}</span>
                                  </p>
                                </div>
                                <div className="text-xs font-mono text-slate-400">
                                  ID Instancia: <span className="text-slate-300">{svc.id}</span>
                                </div>
                              </div>

                              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs font-mono">
                                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                                  <span className="text-slate-500 block mb-1 font-sans font-semibold">Directorios y Procesos</span>
                                  <div className="text-slate-300">
                                    <div><strong>Home:</strong> {svc.home_path || 'No especificado'}</div>
                                    <div className="mt-1">
                                      <strong>Logs:</strong> {svc.logs_path || 'No especificado'}
                                      {svc.logs_path && (
                                        <button
                                          onClick={(e) => handleCopy(svc.logs_path, e)}
                                          className="ml-2 text-indigo-400 hover:text-indigo-300 underline font-sans text-[11px]"
                                        >
                                          Copiar ruta
                                        </button>
                                      )}
                                    </div>
                                    <div className="mt-1"><strong>Usuario SO:</strong> {svc.execution_user}</div>
                                  </div>
                                </div>

                                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                                  <span className="text-slate-500 block mb-1 font-sans font-semibold">Red y Endpoints</span>
                                  <div className="text-slate-300">
                                    <div><strong>Puerto Servicio:</strong> {svc.service_port || 'N/A'}</div>
                                    <div className="mt-1"><strong>Puerto Admin:</strong> {svc.admin_port || 'N/A'}</div>
                                    <div className="mt-1">
                                      <strong>URL-ADMON:</strong>{' '}
                                      {svc.admin_url ? (
                                        <a href={svc.admin_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">
                                          {svc.admin_url}
                                        </a>
                                      ) : (
                                        'No configurada'
                                      )}
                                    </div>
                                    {svc.python_interpreter && (
                                      <div className="mt-1 text-amber-400">
                                        <strong>Python:</strong> {svc.python_interpreter}
                                      </div>
                                    )}
                                  </div>
                                </div>

                                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800/80">
                                  <span className="text-slate-500 block mb-1 font-sans font-semibold">Infraestructura Anfitriona</span>
                                  <div className="text-slate-300">
                                    <div><strong>Servidor Físico / Blade:</strong> {svc.physical_host || 'Virtual / Cloud'}</div>
                                    <div className="mt-1"><strong>IP Producción:</strong> {svc.ip_produccion || 'N/A'}</div>
                                    <div className="mt-1"><strong>IP Respaldo:</strong> {svc.ip_backup || 'N/A'}</div>
                                    {svc.monitoring_url && (
                                      <div className="mt-1">
                                        <strong>SiteScope:</strong>{' '}
                                        <a href={svc.monitoring_url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">
                                          Abrir Monitor
                                        </a>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>

                              {svc.notes && (
                                <div className="mt-3 p-3 bg-slate-950 rounded-lg border border-slate-800/80 text-xs text-slate-400">
                                  <strong className="text-slate-300 block mb-0.5">Observaciones y Casos PAM:</strong>
                                  <div className="whitespace-pre-line font-mono">{svc.notes}</div>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

export default ServerDashboard;

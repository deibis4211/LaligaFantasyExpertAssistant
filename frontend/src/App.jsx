import React, { useState, useEffect, useMemo } from 'react';
import './App.css';

const API_BASE = 'http://127.0.0.1:8000/api';

// Helper to normalize strings for robust accent-insensitive & alias comparison
const normalizeStr = (str) => {
  if (!str) return '';
  return str
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // Remove accents: "Espí" -> "espi"
    .toLowerCase()
    .trim();
};

const isMatchName = (listName, targetName) => {
  const a = normalizeStr(listName);
  const b = normalizeStr(targetName);
  if (!a || !b) return false;
  return a === b || b.includes(a) || a.includes(b);
};

// Helper to get initials from a full name (e.g. "Carlos Espí" -> "CE")
const getInitials = (name) => {
  if (!name) return '⚽';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
};

// Player Avatar component: tries official CDN photo, falls back to elegant FIFA-style badge avatar
const PlayerAvatar = ({ id, name, pos, className = "card-avatar" }) => {
  const [imgError, setImgError] = useState(false);
  const photoUrl = `https://cf.biwenger.com/api/v2/players/${id}/image`;

  if (imgError || !id) {
    return (
      <div className={`initials-avatar pos-bg-${pos} ${className}`} title={name}>
        <span>{getInitials(name)}</span>
      </div>
    );
  }

  return (
    <img 
      src={photoUrl} 
      alt={name}
      onError={() => setImgError(true)}
      className={className}
    />
  );
};

// Streak Dots Renderer
const StreakDots = ({ points }) => {
  if (!points || !Array.isArray(points)) return null;
  return (
    <div className="streak-dots">
      {points.map((pt, idx) => {
        let colorClass = 'dot-red';
        if (pt >= 6) colorClass = 'dot-green';
        else if (pt >= 2) colorClass = 'dot-yellow';
        return (
          <span key={idx} className={`streak-dot ${colorClass}`} title={`Jornada: ${pt} pts`}>
            {pt}
          </span>
        );
      })}
    </div>
  );
};

function App() {
  const [data, setData] = useState(null);
  const [activeTab, setActiveTab] = useState('onces'); // 'onces', 'explorer', 'plantilla', 'mercado', 'alertas', 'config'
  const [selectedOnceIndex, setSelectedOnceIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // All players database for Explorer & Autocomplete
  const [allPlayersData, setAllPlayersData] = useState({ players: [], teams: [] });
  const [loadingExplorer, setLoadingExplorer] = useState(false);

  // Explorer filters
  const [searchQuery, setSearchQuery] = useState('');
  const [posFilter, setPosFilter] = useState('TODOS');
  const [teamFilter, setTeamFilter] = useState('TODOS');
  const [sortBy, setSortBy] = useState('xP'); // 'xP', 'Media', 'Valor', 'WMA'

  // Config raw lists
  const [configPlantilla, setConfigPlantilla] = useState([]);
  const [configMercado, setConfigMercado] = useState([]);

  // Modal selector for adding players
  const [showAddModal, setShowAddModal] = useState(null); // 'plantilla' | 'mercado' | null
  const [modalSearch, setModalSearch] = useState('');

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/data`);
      const json = await res.json();
      setData(json);
      
      // Load config list
      const configRes = await fetch(`${API_BASE}/config`);
      const configJson = await configRes.json();
      setConfigPlantilla(configJson.plantilla || []);
      setConfigMercado(configJson.mercado || []);
    } catch (err) {
      console.error("Error cargando datos:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllPlayers = async () => {
    if (allPlayersData.players.length > 0) return;
    setLoadingExplorer(true);
    try {
      const res = await fetch(`${API_BASE}/players/all`);
      const json = await res.json();
      setAllPlayersData(json);
    } catch (err) {
      console.error("Error cargando todos los jugadores:", err);
    } finally {
      setLoadingExplorer(false);
    }
  };

  useEffect(() => {
    fetchData();
    fetchAllPlayers();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await fetch(`${API_BASE}/refresh`, { method: 'POST' });
      if (res.ok) {
        setAllPlayersData({ players: [], teams: [] });
        await fetchData();
        await fetchAllPlayers();
      }
    } catch (err) {
      console.error("Error al refrescar:", err);
    } finally {
      setRefreshing(false);
    }
  };

  const saveUpdatedConfig = async (newPlantilla, newMercado) => {
    setRefreshing(true);
    try {
      const res = await fetch(`${API_BASE}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plantilla: newPlantilla,
          mercado: newMercado
        })
      });
      if (res.ok) {
        setConfigPlantilla(newPlantilla);
        setConfigMercado(newMercado);
        await fetchData();
      }
    } catch (err) {
      console.error("Error guardando plantilla/mercado:", err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleAddPlayer = (playerName, targetList) => {
    if (targetList === 'plantilla') {
      if (!configPlantilla.some(n => isMatchName(n, playerName))) {
        const updated = [...configPlantilla, playerName];
        saveUpdatedConfig(updated, configMercado);
      }
    } else if (targetList === 'mercado') {
      if (!configMercado.some(n => isMatchName(n, playerName))) {
        const updated = [...configMercado, playerName];
        saveUpdatedConfig(configPlantilla, updated);
      }
    }
  };

  const handleRemovePlayer = (playerName, targetList) => {
    if (targetList === 'plantilla') {
      const updated = configPlantilla.filter(n => !isMatchName(n, playerName));
      saveUpdatedConfig(updated, configMercado);
    } else if (targetList === 'mercado') {
      const updated = configMercado.filter(n => !isMatchName(n, playerName));
      saveUpdatedConfig(configPlantilla, updated);
    }
  };

  // Filtered & Sorted All Players for Explorer
  const filteredPlayers = useMemo(() => {
    let list = [...allPlayersData.players];

    if (searchQuery.trim()) {
      const q = normalizeStr(searchQuery);
      list = list.filter(p => normalizeStr(p.Nombre).includes(q) || normalizeStr(p.Equipo).includes(q));
    }

    if (posFilter !== 'TODOS') {
      list = list.filter(p => p.Posicion === posFilter);
    }

    if (teamFilter !== 'TODOS') {
      list = list.filter(p => p.Equipo === teamFilter);
    }

    list.sort((a, b) => {
      if (sortBy === 'xP') return (b.xP || 0) - (a.xP || 0);
      if (sortBy === 'Media') return b.Media - a.Media;
      if (sortBy === 'Valor') return b.Valor - a.Valor;
      if (sortBy === 'WMA') return (b.WMA || 0) - (a.WMA || 0);
      return 0;
    });

    return list;
  }, [allPlayersData.players, searchQuery, posFilter, teamFilter, sortBy]);

  if (loading) {
    return (
      <div className="loader-container">
        <div className="loader-football">⚽</div>
        <h2>Entrenando modelos XGBoost...</h2>
        <p>Conectando con Biwenger y procesando estadísticas de racha...</p>
      </div>
    );
  }

  const { plantilla, mercado, alertas, onces_ideales, presupuesto } = data || {};
  const currentOnceObj = onces_ideales && onces_ideales[selectedOnceIndex];

  // Helper for 2D Pitch Layout
  const getCoordinates = (pos, index, totalOfPosition, formationStr) => {
    const [df, mc, dl] = formationStr.split('-').map(Number);
    if (pos === 'PT') return { left: '50%', top: '88%' };
    
    let y = '50%';
    let count = 0;
    if (pos === 'DF') { y = '65%'; count = df; }
    else if (pos === 'MC') { y = '40%'; count = mc; }
    else if (pos === 'DL') { y = '15%'; count = dl; }
    
    const step = 80 / (count + 1);
    const x = 10 + step * (index + 1);
    return { left: `${x}%`, top: y };
  };

  const getPositionCoordinatesMap = (oncePlayers, formationStr) => {
    const counts = { PT: 0, DF: 0, MC: 0, DL: 0 };
    return oncePlayers.map(p => {
      const idx = counts[p.Posicion];
      counts[p.Posicion] += 1;
      const total = p.Posicion === 'PT' ? 1 : Number(formationStr.split('-')[p.Posicion === 'DF' ? 0 : p.Posicion === 'MC' ? 1 : 2]);
      return {
        player: p,
        coords: getCoordinates(p.Posicion, idx, total, formationStr)
      };
    });
  };

  const onceCoords = currentOnceObj 
    ? getPositionCoordinatesMap(currentOnceObj.once, currentOnceObj.formacion)
    : [];

  return (
    <div className="app-container">
      {refreshing && (
        <div className="refresh-overlay">
          <div className="loader-football">⚽</div>
          <h3>Actualizando base de datos en vivo...</h3>
        </div>
      )}

      {/* Quick Add Player Modal */}
      {showAddModal && (
        <div className="modal-backdrop" onClick={() => setShowAddModal(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Añadir Jugador a {showAddModal === 'plantilla' ? 'Mi Plantilla' : 'Mercado'}</h3>
              <button className="btn-close-modal" onClick={() => setShowAddModal(null)}>✖</button>
            </div>
            <input 
              type="text" 
              className="modal-search-input"
              placeholder="Buscar por nombre o equipo..."
              value={modalSearch}
              onChange={(e) => setModalSearch(e.target.value)}
              autoFocus
            />
            <div className="modal-players-list">
              {allPlayersData.players
                .filter(p => normalizeStr(p.Nombre).includes(normalizeStr(modalSearch)) || normalizeStr(p.Equipo).includes(normalizeStr(modalSearch)))
                .slice(0, 15)
                .map(p => {
                  const isAdded = showAddModal === 'plantilla' 
                    ? configPlantilla.some(n => isMatchName(n, p.Nombre))
                    : configMercado.some(n => isMatchName(n, p.Nombre));
                  return (
                    <div key={p.ID} className="modal-player-item">
                      <PlayerAvatar id={p.ID} name={p.Nombre} pos={p.Posicion} className="modal-avatar" />
                      <div className="modal-item-info">
                        <strong>{p.Nombre}</strong>
                        <span>{p.Equipo} • <span className={`badge-pos pos-${p.Posicion}`}>{p.Posicion}</span></span>
                      </div>
                      <span className="modal-item-val">{p.Valor.toLocaleString()} €</span>
                      <button 
                        className={`btn-action-add ${isAdded ? 'added' : ''}`}
                        disabled={isAdded}
                        onClick={() => {
                          handleAddPlayer(p.Nombre, showAddModal);
                          setShowAddModal(null);
                        }}
                      >
                        {isAdded ? '✓ Añadido' : '+ Añadir'}
                      </button>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="main-header">
        <div className="header-brand">
          <span className="logo-emoji">⚽</span>
          <h1>LALIGA FANTASY <span className="neon-text">EXPERT</span></h1>
        </div>
        <div className="header-stats">
          <div className="stat-pill">
            <span className="label">Presupuesto:</span>
            <span className="value font-mono">{presupuesto?.toLocaleString()} €</span>
          </div>
          <button className="btn-refresh" onClick={handleRefresh} title="Actualizar datos y reentrenar">
            🔄 Recargar API
          </button>
        </div>
      </header>

      {/* Sidebar & Core Workspace */}
      <div className="workspace">
        <aside className="sidebar">
          <nav className="nav-menu">
            <button 
              className={`nav-item ${activeTab === 'onces' ? 'active' : ''}`}
              onClick={() => setActiveTab('onces')}
            >
              📋 Onces Ideales
            </button>
            <button 
              className={`nav-item ${activeTab === 'explorer' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('explorer');
                fetchAllPlayers();
              }}
            >
              🔍 Explorador LaLiga
            </button>
            <button 
              className={`nav-item ${activeTab === 'plantilla' ? 'active' : ''}`}
              onClick={() => setActiveTab('plantilla')}
            >
              👥 Mi Plantilla ({plantilla?.length})
            </button>
            <button 
              className={`nav-item ${activeTab === 'mercado' ? 'active' : ''}`}
              onClick={() => setActiveTab('mercado')}
            >
              🛒 Mercado de Hoy ({mercado?.length})
            </button>
            <button 
              className={`nav-item ${activeTab === 'alertas' ? 'active' : ''}`}
              onClick={() => setActiveTab('alertas')}
            >
              ⚠️ Alertas de Venta ({alertas?.length})
            </button>
            <button 
              className={`nav-item ${activeTab === 'config' ? 'active' : ''}`}
              onClick={() => setActiveTab('config')}
            >
              ⚙️ Configurar Listas
            </button>
          </nav>
        </aside>

        <main className="content-area">
          {/* TAB: ONCES IDEALES */}
          {activeTab === 'onces' && (
            <div className="tab-onces">
              <div className="onces-selector-container">
                <h2>Top 5 Formaciones Ideales (XGBoost)</h2>
                <div className="onces-selector">
                  {onces_ideales?.map((once, idx) => (
                    <button
                      key={idx}
                      className={`once-selector-card ${selectedOnceIndex === idx ? 'active' : ''}`}
                      onClick={() => setSelectedOnceIndex(idx)}
                    >
                      <span className="option-num">Opción #{idx + 1}</span>
                      <span className="formation-name">{once.formacion}</span>
                      <span className="xp-badge">{once.xp_total.toFixed(2)} xP</span>
                    </button>
                  ))}
                </div>
              </div>

              {currentOnceObj ? (
                <div className="tactical-layout">
                  {/* Tactical Board (2D Pitch) */}
                  <div className="pitch-container">
                    <div className="pitch">
                      <div className="pitch-center-circle"></div>
                      <div className="pitch-center-line"></div>
                      <div className="pitch-penalty-area-top"></div>
                      <div className="pitch-penalty-area-bottom"></div>
                      
                      {onceCoords.map(({ player, coords }, idx) => (
                        <div 
                          key={player.ID + idx}
                          className="pitch-player-card"
                          style={{ left: coords.left, top: coords.top }}
                        >
                          <div className="player-avatar-wrapper">
                            <PlayerAvatar id={player.ID} name={player.Nombre} pos={player.Posicion} className="player-avatar" />
                            <span className={`pos-badge pos-${player.Posicion}`}>{player.Posicion}</span>
                          </div>
                          <span className="player-pitch-name">{player.Nombre}</span>
                          <span className="player-pitch-xp">{player.xP.toFixed(1)} xP</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Once Details List */}
                  <div className="once-details">
                    <h3>Detalles de la Alineación</h3>
                    <div className="details-table-wrapper">
                      <table className="custom-table">
                        <thead>
                          <tr>
                            <th>Nombre</th>
                            <th>Pos</th>
                            <th>Equipo</th>
                            <th>Media</th>
                            <th>xP</th>
                            <th>Valor</th>
                          </tr>
                        </thead>
                        <tbody>
                          {currentOnceObj.once.map((p, idx) => (
                            <tr key={idx}>
                              <td><strong>{p.Nombre}</strong></td>
                              <td><span className={`badge-pos pos-${p.Posicion}`}>{p.Posicion}</span></td>
                              <td>{p.Equipo}</td>
                              <td>{p.Media.toFixed(1)}</td>
                              <td className="xp-text font-bold">{p.xP.toFixed(1)}</td>
                              <td className="font-mono">{p.Valor.toLocaleString()} €</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="empty-state">
                  <p>❌ No hay suficientes jugadores válidos en la plantilla para formar un Once legal.</p>
                </div>
              )}
            </div>
          )}

          {/* TAB: EXPLORADOR LALIGA */}
          {activeTab === 'explorer' && (
            <div className="tab-explorer">
              <div className="tab-header-flex">
                <div>
                  <h2>🔍 Explorador de Jugadores de LaLiga</h2>
                  <p className="subtitle">Inspecciona los ~560 jugadores con estadísticas de racha y predicciones de xP en tiempo real.</p>
                </div>
                <span className="count-pill">{filteredPlayers.length} Jugadores</span>
              </div>

              {/* Filters Bar */}
              <div className="explorer-filters-bar">
                <input 
                  type="text" 
                  className="filter-search-input"
                  placeholder="🔍 Buscar por nombre o equipo..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />

                <div className="filter-group">
                  <label>Posición:</label>
                  <select value={posFilter} onChange={(e) => setPosFilter(e.target.value)}>
                    <option value="TODOS">Todas las posiciones</option>
                    <option value="PT">Porteros (PT)</option>
                    <option value="DF">Defensas (DF)</option>
                    <option value="MC">Centrocampistas (MC)</option>
                    <option value="DL">Delanteros (DL)</option>
                  </select>
                </div>

                <div className="filter-group">
                  <label>Equipo:</label>
                  <select value={teamFilter} onChange={(e) => setTeamFilter(e.target.value)}>
                    <option value="TODOS">Todos los equipos</option>
                    {allPlayersData.teams.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>

                <div className="filter-group">
                  <label>Ordenar por:</label>
                  <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                    <option value="xP">xP Proyectado (XGBoost)</option>
                    <option value="Media">Media de Puntos</option>
                    <option value="WMA">Racha WMA</option>
                    <option value="Valor">Valor de Mercado</option>
                  </select>
                </div>
              </div>

              {/* Player Cards Grid */}
              {loadingExplorer ? (
                <div className="loader-container" style={{ height: '300px' }}>
                  <div className="loader-football">⚽</div>
                  <p>Cargando base de datos completa de LaLiga...</p>
                </div>
              ) : (
                <div className="grid-players">
                  {filteredPlayers.map((p) => {
                    const inPlantilla = configPlantilla.some(n => isMatchName(n, p.Nombre));
                    const inMercado = configMercado.some(n => isMatchName(n, p.Nombre));

                    return (
                      <div className="player-card explorer-card" key={p.ID}>
                        <div className="player-card-header">
                          <PlayerAvatar id={p.ID} name={p.Nombre} pos={p.Posicion} className="card-avatar" />
                          <div className="card-header-info">
                            <h3>{p.Nombre}</h3>
                            <span className="team-label">{p.Equipo}</span>
                          </div>
                          <span className={`card-pos pos-${p.Posicion}`}>{p.Posicion}</span>
                        </div>
                        
                        <div className="player-card-body">
                          <div className="card-stat">
                            <span className="stat-label">Valor de Mercado</span>
                            <span className="stat-val font-mono">{p.Valor.toLocaleString()} €</span>
                          </div>
                          
                          <div className="card-stat-grid">
                            <div className="mini-stat">
                              <span className="stat-label">Media</span>
                              <span className="stat-val">{p.Media.toFixed(1)}</span>
                            </div>
                            <div className="mini-stat">
                              <span className="stat-label">xP Proyectado</span>
                              <span className="stat-val xp-highlight font-bold">{p.xP?.toFixed(1) || '0.0'}</span>
                            </div>
                          </div>

                          {/* 5-Match Streak Dots */}
                          <div className="mini-stat">
                            <span className="stat-label">Últimos 5 Partidos:</span>
                            <StreakDots points={p.Puntos_Recientes} />
                          </div>

                          <div className="upcoming-fixture">
                            <span>Próximo: <strong>vs {p.Rival || 'Rival'}</strong> ({p.Localia === 1 ? 'Casa' : 'Fuera'})</span>
                          </div>

                          {/* Quick Add Actions */}
                          <div className="explorer-card-actions">
                            <button 
                              className={`btn-quick-add ${inPlantilla ? 'in-list' : ''}`}
                              disabled={inPlantilla}
                              onClick={() => handleAddPlayer(p.Nombre, 'plantilla')}
                            >
                              {inPlantilla ? '✓ En Plantilla' : '+ Plantilla'}
                            </button>
                            <button 
                              className={`btn-quick-add ${inMercado ? 'in-list' : ''}`}
                              disabled={inMercado}
                              onClick={() => handleAddPlayer(p.Nombre, 'mercado')}
                            >
                              {inMercado ? '✓ En Mercado' : '+ Mercado'}
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB: MI PLANTILLA */}
          {activeTab === 'plantilla' && (
            <div className="tab-plantilla">
              <div className="tab-header-flex">
                <div>
                  <h2>Mi Plantilla</h2>
                  <p className="subtitle">Jugadores en tu equipo actual</p>
                </div>
                <div className="header-actions">
                  <button className="btn-add-player" onClick={() => setShowAddModal('plantilla')}>
                    ➕ Añadir Jugador
                  </button>
                  <span className="count-pill">{plantilla?.length} Jugadores</span>
                </div>
              </div>
              
              <div className="grid-players">
                {plantilla?.map((p, idx) => (
                  <div className="player-card" key={idx}>
                    <button 
                      className="btn-card-remove" 
                      title="Eliminar de la plantilla"
                      onClick={() => handleRemovePlayer(p.Nombre, 'plantilla')}
                    >
                      ✖
                    </button>
                    <div className="player-card-header">
                      <PlayerAvatar id={p.ID} name={p.Nombre} pos={p.Posicion} className="card-avatar" />
                      <div className="card-header-info">
                        <h3>{p.Nombre}</h3>
                        <span className="team-label">{p.Equipo}</span>
                      </div>
                      <span className={`card-pos pos-${p.Posicion}`}>{p.Posicion}</span>
                    </div>
                    
                    <div className="player-card-body">
                      <div className="card-stat">
                        <span className="stat-label">Valor de Mercado</span>
                        <span className="stat-val font-mono">{p.Valor.toLocaleString()} €</span>
                      </div>
                      
                      <div className="card-stat-grid">
                        <div className="mini-stat">
                          <span className="stat-label">Media</span>
                          <span className="stat-val">{p.Media.toFixed(1)}</span>
                        </div>
                        <div className="mini-stat">
                          <span className="stat-label">xP Proyectado</span>
                          <span className="stat-val xp-highlight font-bold">{p.xP?.toFixed(1) || '0.0'}</span>
                        </div>
                      </div>

                      {/* Racha Stats */}
                      <div className="streak-stats">
                        <div className="mini-stat">
                          <span className="stat-label">WMA (Racha)</span>
                          <span className="stat-val font-semibold">{p.WMA?.toFixed(1) || '0.0'}</span>
                        </div>
                        <div className="mini-stat">
                          <span className="stat-label">Últimos partidos</span>
                          <StreakDots points={p.Puntos_Recientes} />
                        </div>
                      </div>
                      
                      <div className="upcoming-fixture">
                        <span>Próximo: <strong>vs {p.Rival}</strong> ({p.Localia === 1 ? 'Casa' : 'Fuera'})</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB: MERCADO DE HOY */}
          {activeTab === 'mercado' && (
            <div className="tab-mercado">
              <div className="tab-header-flex">
                <div>
                  <h2>Fichajes Recomendados</h2>
                  <p className="subtitle">Algoritmo de puntuación sobre 100: Forma (40%) + Tendencia (30%) + Rentabilidad (30%)</p>
                </div>
                <div className="header-actions">
                  <button className="btn-add-player" onClick={() => setShowAddModal('mercado')}>
                    ➕ Añadir al Mercado
                  </button>
                  <span className="count-pill">{mercado?.length} Jugadores</span>
                </div>
              </div>

              <div className="details-table-wrapper">
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th>Jugador</th>
                      <th>Pos</th>
                      <th>Equipo</th>
                      <th>Nota / 100</th>
                      <th>Valor</th>
                      <th>Asequible</th>
                      <th>Tendencia 48h</th>
                      <th>Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mercado?.map((p, idx) => (
                      <tr key={idx}>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
                            <PlayerAvatar id={p.ID} name={p.Nombre} pos={p.Posicion} className="table-avatar" />
                            <strong>{p.Nombre}</strong>
                          </div>
                        </td>
                        <td><span className={`badge-pos pos-${p.Posicion}`}>{p.Posicion}</span></td>
                        <td>{p.Equipo}</td>
                        <td className="score-text font-bold">{p.Nota_Fichaje_100.toFixed(1)}</td>
                        <td className="font-mono">{p.Valor.toLocaleString()} €</td>
                        <td>
                          <span className={`status-pill ${p.Asequible === 'SI' ? 'status-green' : 'status-red'}`}>
                            {p.Asequible}
                          </span>
                        </td>
                        <td className={`font-semibold ${p.Tendencia_48h_pct > 0 ? 'text-green' : p.Tendencia_48h_pct < 0 ? 'text-red' : ''}`}>
                          {p.Tendencia_48h_pct > 0 ? `+${p.Tendencia_48h_pct.toFixed(1)}%` : `${p.Tendencia_48h_pct.toFixed(1)}%`}
                        </td>
                        <td>
                          <button 
                            className="btn-table-remove"
                            onClick={() => handleRemovePlayer(p.Nombre, 'mercado')}
                            title="Quitar del mercado"
                          >
                            ✖ Quitar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB: ALERTAS DE VENTA */}
          {activeTab === 'alertas' && (
            <div className="tab-alertas">
              <div className="tab-header-flex">
                <h2>Alertas de Venta Sugeridas</h2>
                <p className="subtitle">Detecta lesionados, sancionados, bajadas drásticas de valor o bajo xP en comparación con su media.</p>
              </div>

              {alertas?.length > 0 ? (
                <div className="details-table-wrapper">
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Jugador</th>
                        <th>Posición</th>
                        <th>Estado</th>
                        <th>Tendencia 48h</th>
                        <th>xP</th>
                        <th>Motivo Venta</th>
                      </tr>
                    </thead>
                    <tbody>
                      {alertas.map((p, idx) => (
                        <tr key={idx} className="alert-row">
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
                              <PlayerAvatar id={p.ID} name={p.Nombre} pos={p.Posicion} className="table-avatar" />
                              <strong>{p.Nombre}</strong>
                            </div>
                          </td>
                          <td><span className={`badge-pos pos-${p.Posicion}`}>{p.Posicion}</span></td>
                          <td>
                            <span className={`status-pill ${p.Estado === 'Disponible' ? 'status-green' : 'status-red'}`}>
                              {p.Estado}
                            </span>
                          </td>
                          <td className="text-red font-semibold">{p.Tendencia_48h_pct.toFixed(1)}%</td>
                          <td className="font-bold">{p.xP.toFixed(1)}</td>
                          <td className="text-orange font-medium">{p.Motivo_Venta}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="success-state">
                  <h3>✅ Tu plantilla está en perfecto estado</h3>
                  <p>No se han detectado lesionados, caídas de valor de mercado drásticas ni desplomes de rendimiento proyectado.</p>
                </div>
              )}
            </div>
          )}

          {/* TAB: CONFIGURACIÓN TAGS */}
          {activeTab === 'config' && (
            <div className="tab-config">
              <h2>Configurar Listas de Selección</h2>
              <p className="subtitle">Administra los jugadores de tu plantilla y mercado mediante etiquetas visuales sencillas.</p>
              
              <div className="config-flex">
                {/* Plantilla Tags */}
                <div className="config-editor">
                  <div className="config-box-header">
                    <h3>👥 Mi Plantilla ({configPlantilla.length})</h3>
                    <button className="btn-add-player-sm" onClick={() => setShowAddModal('plantilla')}>
                      + Añadir
                    </button>
                  </div>
                  <div className="tags-container">
                    {configPlantilla.map(name => (
                      <span className="player-tag" key={name}>
                        {name}
                        <button className="btn-tag-remove" onClick={() => handleRemovePlayer(name, 'plantilla')}>✖</button>
                      </span>
                    ))}
                  </div>
                </div>
                
                {/* Mercado Tags */}
                <div className="config-editor">
                  <div className="config-box-header">
                    <h3>🛒 Mercado de Hoy ({configMercado.length})</h3>
                    <button className="btn-add-player-sm" onClick={() => setShowAddModal('mercado')}>
                      + Añadir
                    </button>
                  </div>
                  <div className="tags-container">
                    {configMercado.map(name => (
                      <span className="player-tag tag-mercado" key={name}>
                        {name}
                        <button className="btn-tag-remove" onClick={() => handleRemovePlayer(name, 'mercado')}>✖</button>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;

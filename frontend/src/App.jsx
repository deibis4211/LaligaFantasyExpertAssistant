import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = 'http://127.0.0.1:8000/api';

// Fallback image helper
const getPlayerPhoto = (id, slug) => {
  return `https://cf.biwenger.com/api/v2/players/${id}/image`;
};

function App() {
  const [data, setData] = useState(null);
  const [activeTab, setActiveTab] = useState('onces'); // 'onces', 'plantilla', 'mercado', 'alertas', 'config'
  const [selectedOnceIndex, setSelectedOnceIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // Config state
  const [configPlantilla, setConfigPlantilla] = useState('');
  const [configMercado, setConfigMercado] = useState('');

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/data`);
      const json = await res.json();
      setData(json);
      
      // Load config too
      const configRes = await fetch(`${API_BASE}/config`);
      const configJson = await configRes.json();
      setConfigPlantilla(configJson.plantilla.join('\n'));
      setConfigMercado(configJson.mercado.join('\n'));
    } catch (err) {
      console.error("Error cargando datos:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await fetch(`${API_BASE}/refresh`, { method: 'POST' });
      if (res.ok) {
        await fetchData();
      }
    } catch (err) {
      console.error("Error al refrescar:", err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleSaveConfig = async () => {
    setRefreshing(true);
    try {
      const res = await fetch(`${API_BASE}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plantilla: configPlantilla.split('\n').map(s => s.trim()).filter(Boolean),
          mercado: configMercado.split('\n').map(s => s.trim()).filter(Boolean)
        })
      });
      if (res.ok) {
        await fetchData();
        alert("¡Plantilla y Mercado guardados con éxito! Los modelos se han reentrenado.");
      }
    } catch (err) {
      console.error("Error guardando config:", err);
    } finally {
      setRefreshing(false);
    }
  };

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

  // Helper to map positions for 2D tactical board
  const getCoordinates = (pos, index, totalOfPosition, formationStr) => {
    // formationStr like "4-3-3" -> [df, mc, dl]
    const [df, mc, dl] = formationStr.split('-').map(Number);
    
    // Y-coordinates: PT=90%, DF=65%, MC=40%, DL=15%
    if (pos === 'PT') {
      return { left: '50%', top: '88%' };
    }
    
    let y = '50%';
    let count = 0;
    if (pos === 'DF') {
      y = '65%';
      count = df;
    } else if (pos === 'MC') {
      y = '40%';
      count = mc;
    } else if (pos === 'DL') {
      y = '15%';
      count = dl;
    }
    
    // Spread evenly horizontally
    // If count is 4, positions at 15%, 38%, 62%, 85%
    const step = 80 / (count + 1);
    const x = 10 + step * (index + 1);
    return { left: `${x}%`, top: y };
  };

  // Group current once by positions to compute coordinates
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
              ⚙️ Editar Datos (.txt)
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
                      
                      {/* Players on Pitch */}
                      {onceCoords.map(({ player, coords }, idx) => (
                        <div 
                          key={player.ID + idx}
                          className="pitch-player-card"
                          style={{ left: coords.left, top: coords.top }}
                        >
                          <div className="player-avatar-wrapper">
                            <img 
                              src={getPlayerPhoto(player.ID, player.slug)} 
                              alt={player.Nombre}
                              onError={(e) => {
                                e.target.onerror = null; 
                                e.target.src = `https://api.dicebear.com/7.x/initials/svg?seed=${player.Nombre}&backgroundColor=38bdf8`;
                              }}
                              className="player-avatar"
                            />
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

          {/* TAB: MI PLANTILLA */}
          {activeTab === 'plantilla' && (
            <div className="tab-plantilla">
              <div className="tab-header-flex">
                <h2>Mi Plantilla</h2>
                <span className="count-pill">{plantilla?.length} Jugadores</span>
              </div>
              
              <div className="grid-players">
                {plantilla?.map((p, idx) => (
                  <div className="player-card" key={idx}>
                    <div className="player-card-header">
                      <img 
                        src={getPlayerPhoto(p.ID, p.slug)} 
                        alt={p.Nombre}
                        onError={(e) => {
                          e.target.onerror = null; 
                          e.target.src = `https://api.dicebear.com/7.x/initials/svg?seed=${p.Nombre}&backgroundColor=10b981`;
                        }}
                        className="card-avatar"
                      />
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
                          <span className="stat-label">Tendencia</span>
                          <span className={`stat-val font-semibold ${p.Tendencia > 0 ? 'text-green' : p.Tendencia < 0 ? 'text-red' : ''}`}>
                            {p.Tendencia > 0 ? `+${p.Tendencia}` : p.Tendencia || '0'}
                          </span>
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
                <h2>Fichajes Recomendados</h2>
                <p className="subtitle">Algoritmo de puntuación sobre 100: Forma (40%) + Tendencia (30%) + Rentabilidad (30%)</p>
              </div>

              <div className="details-table-wrapper">
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th>Nombre</th>
                      <th>Pos</th>
                      <th>Equipo</th>
                      <th>Nota / 100</th>
                      <th>Valor</th>
                      <th>Asequible</th>
                      <th>Tendencia 48h</th>
                      <th>Media</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mercado?.map((p, idx) => (
                      <tr key={idx}>
                        <td><strong>{p.Nombre}</strong></td>
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
                        <td>{p.Media.toFixed(1)}</td>
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
                        <th>Nombre</th>
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
                          <td><strong>{p.Nombre}</strong></td>
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

          {/* TAB: CONFIGURACIÓN TXT */}
          {activeTab === 'config' && (
            <div className="tab-config">
              <h2>Editar Plantilla y Mercado (.txt)</h2>
              <p className="subtitle">Modifica los archivos de texto directamente desde aquí. Los cambios se guardarán automáticamente en tu servidor local.</p>
              
              <div className="config-flex">
                <div className="config-editor">
                  <h3>Mi Plantilla (un nombre por línea)</h3>
                  <textarea
                    value={configPlantilla}
                    onChange={(e) => setConfigPlantilla(e.target.value)}
                    className="txt-textarea"
                    placeholder="Sergio Herrera&#10;Carlos Romero&#10;..."
                  />
                </div>
                
                <div className="config-editor">
                  <h3>Mercado de Hoy (un nombre por línea)</h3>
                  <textarea
                    value={configMercado}
                    onChange={(e) => setConfigMercado(e.target.value)}
                    className="txt-textarea"
                    placeholder="Espí&#10;Gavi&#10;..."
                  />
                </div>
              </div>
              
              <div className="config-actions">
                <button className="btn-save" onClick={handleSaveConfig}>
                  💾 Guardar Cambios y Entrenar
                </button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;

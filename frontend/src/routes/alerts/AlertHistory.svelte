<script>
  export let history = [];
  export let stats = null;
  
  function formatDate(dateString) {
    return new Date(dateString).toLocaleString('fr-FR');
  }
  
  function getRiskColor(risk) {
    switch(risk) {
      case 'extreme': return '#ef4444';
      case 'high': return '#f59e0b';
      case 'medium': return '#3b82f6';
      case 'low': return '#10b981';
      default: return '#64748b';
    }
  }
</script>

<div class="history-container">
  <!-- Stats Summary -->
  {#if stats}
    <div class="stats-summary">
      <h3>📊 Statistiques (30 derniers jours)</h3>
      
      <div class="stats-grid">
        <div class="stat-card">
          <span class="stat-value">{stats.summary?.total_alerts_sent || 0}</span>
          <span class="stat-label">Alertes envoyées</span>
        </div>
        
        <div class="stat-card">
          <span class="stat-value">{stats.summary?.accuracy_rate || 0}%</span>
          <span class="stat-label">Taux de précision</span>
        </div>
        
        <div class="stat-card">
          <span class="stat-value">{stats.summary?.avg_movement || 0}</span>
          <span class="stat-label">Mouvement moyen (pips)</span>
        </div>
        
        <div class="stat-card">
          <span class="stat-value">{stats.summary?.extreme_alerts || 0}</span>
          <span class="stat-label">Alertes EXTRÊMES</span>
        </div>
      </div>
    </div>
  {/if}
  
  <!-- History List -->
  <div class="history-section">
    <h3>📜 Historique des Alertes</h3>
    
    {#if history.length === 0}
      <div class="empty-state">
        <span class="emoji">📭</span>
        <p>Aucun historique d'alertes</p>
      </div>
    {:else}
      <div class="history-list">
        {#each history as alert}
          <div class="history-item">
            <div class="item-header">
              <div class="item-title">
                <span class="currency-badge">{alert.symbol}</span>
                <h4>{alert.event_name}</h4>
              </div>
              <span class="risk-badge" style="background-color: {getRiskColor(alert.risk_level)}">
                {alert.risk_level?.toUpperCase()}
              </span>
            </div>
            
            <div class="item-details">
              <div class="detail-row">
                <span class="label">📅 Date:</span>
                <span class="value">{formatDate(alert.event_date)}</span>
              </div>
              
              <div class="detail-row">
                <span class="label">📊 Mouvement prévu:</span>
                <span class="value">{alert.predicted_movement || 'N/A'} pips</span>
              </div>
              
              {#if alert.actual_movement}
                <div class="detail-row">
                  <span class="label">✅ Mouvement réel:</span>
                  <span class="value">{alert.actual_movement} pips</span>
                </div>
              {/if}
              
              <div class="detail-row">
                <span class="label">🎯 Confiance:</span>
                <span class="value">{alert.confidence || 'N/A'}</span>
              </div>
              
              <div class="detail-row">
                <span class="label">📨 Envoyée:</span>
                <span class="value">{formatDate(alert.sent_at)}</span>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .history-container {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }
  
  h3 {
    font-size: 1.3rem;
    color: #1e293b;
    margin-bottom: 1rem;
  }
  
  .stats-summary {
    background: #f8fafc;
    padding: 1.5rem;
    border-radius: 12px;
  }
  
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
  }
  
  .stat-card {
    background: white;
    padding: 1.5rem;
    border-radius: 8px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }
  
  .stat-value {
    display: block;
    font-size: 2rem;
    font-weight: 700;
    color: #3b82f6;
    margin-bottom: 0.5rem;
  }
  
  .stat-label {
    font-size: 0.85rem;
    color: #64748b;
  }
  
  .history-section {
    background: #f8fafc;
    padding: 1.5rem;
    border-radius: 12px;
  }
  
  .empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: #64748b;
  }
  
  .empty-state .emoji {
    font-size: 3rem;
    display: block;
    margin-bottom: 1rem;
  }
  
  .history-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  
  .history-item {
    background: white;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }
  
  .item-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #e2e8f0;
  }
  
  .item-title {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }
  
  .currency-badge {
    background: #3b82f6;
    color: white;
    padding: 0.25rem 0.75rem;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.85rem;
  }
  
  .item-title h4 {
    font-size: 1.1rem;
    color: #1e293b;
    margin: 0;
  }
  
  .risk-badge {
    padding: 0.4rem 0.8rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    color: white;
  }
  
  .item-details {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .detail-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem;
    background: #f8fafc;
    border-radius: 6px;
  }
  
  .label {
    font-size: 0.9rem;
    color: #64748b;
    font-weight: 600;
  }
  
  .value {
    font-size: 0.9rem;
    color: #1e293b;
    font-weight: 600;
  }
</style>

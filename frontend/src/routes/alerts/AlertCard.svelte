<script>
    export let alert;
    
    const riskColors = {
      'extreme': { bg: '#fee2e2', border: '#ef4444', text: '#991b1b' },
      'high': { bg: '#fed7aa', border: '#f59e0b', text: '#92400e' },
      'medium': { bg: '#fef3c7', border: '#fbbf24', text: '#78350f' },
      'low': { bg: '#d1fae5', border: '#10b981', text: '#065f46' }
    };
    
    const riskEmojis = {
      'extreme': '🔴🔴🔴',
      'high': '🟠🟠',
      'medium': '🟡',
      'low': '🟢'
    };
    
    $: risk = alert.prediction.risk_level;
    $: colors = riskColors[risk] || riskColors.medium;
    $: dirProbs = alert.prediction.direction_probability;
    $: dominantDir = Object.keys(dirProbs).reduce((a, b) => dirProbs[a] > dirProbs[b] ? a : b);
  </script>
  
  <div class="alert-card" style="border-left-color: {colors.border}; background: {colors.bg}">
    <div class="alert-header">
      <div class="time-badge">
        ⏰ {alert.time_until_event}
      </div>
      <div class="risk-badge" style="background: {colors.border}20; color: {colors.text}">
        {riskEmojis[risk]} {risk.toUpperCase()}
      </div>
    </div>
    
    <div class="event-info">
      <h3 class="event-name">{alert.event.event_name}</h3>
      <div class="event-meta">
        <span class="meta-item">
          💱 <strong>{alert.symbol}</strong>
        </span>
        <span class="meta-item">
          📅 {alert.event.date} {alert.event.time}
        </span>
        <span class="meta-item">
          🌍 {alert.event.currency}
        </span>
      </div>
    </div>
    
    <div class="prediction-box">
      <div class="prediction-row">
        <span class="label">Mouvement attendu</span>
        <span class="value big">{alert.prediction.expected_movement_pips} pips</span>
      </div>
      
      <div class="prediction-row">
        <span class="label">Confiance</span>
        <span class="value">
          {alert.prediction.confidence.toUpperCase()} 
          ({alert.prediction.historical_samples} samples)
        </span>
      </div>
      
      <div class="prediction-row">
        <span class="label">Direction probable</span>
        <span class="value">
          {#if dominantDir === 'up'}📈{:else if dominantDir === 'down'}📉{:else}↔️{/if}
          {dominantDir.toUpperCase()} ({dirProbs[dominantDir]}%)
        </span>
      </div>
    </div>
    
    <div class="recommendation">
      <strong>💡 Conseil:</strong>
      <p>{alert.recommendation}</p>
    </div>
  </div>
  
  <style>
    .alert-card {
      border-left: 4px solid;
      border-radius: 12px;
      padding: 1.5rem;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .alert-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .alert-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
    }
    
    .time-badge, .risk-badge {
      padding: 0.5rem 1rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 700;
    }
    
    .time-badge {
      background: white;
    }
    
    .event-info {
      margin-bottom: 1rem;
    }
    
    .event-name {
      font-size: 1.1rem;
      color: #1e293b;
      margin-bottom: 0.5rem;
      line-height: 1.3;
    }
    
    .event-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      font-size: 0.85rem;
      color: #64748b;
    }
    
    .prediction-box {
      background: white;
      padding: 1rem;
      border-radius: 8px;
      margin-bottom: 1rem;
    }
    
    .prediction-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.5rem 0;
      border-bottom: 1px solid #f1f5f9;
    }
    
    .prediction-row:last-child {
      border-bottom: none;
    }
    
    .label {
      font-size: 0.85rem;
      color: #64748b;
    }
    
    .value {
      font-weight: 600;
      color: #1e293b;
    }
    
    .value.big {
      font-size: 1.2rem;
      color: #3b82f6;
    }
    
    .recommendation {
      background: white;
      padding: 1rem;
      border-radius: 8px;
      font-size: 0.9rem;
    }
    
    .recommendation strong {
      display: block;
      margin-bottom: 0.5rem;
      color: #1e293b;
    }
    
    .recommendation p {
      color: #475569;
      line-height: 1.5;
      margin: 0;
    }
  </style>
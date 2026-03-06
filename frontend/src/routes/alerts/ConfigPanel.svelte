<script>
    import { createEventDispatcher } from 'svelte';
    
    export let settings;
    
    const dispatch = createEventDispatcher();
    
    let localSettings = { ...settings };
    
    const availableSymbols = [
      { value: 'EURUSD', label: 'EUR/USD 💶' },
      { value: 'GBPUSD', label: 'GBP/USD 💷' },
      { value: 'USDJPY', label: 'USD/JPY 💴' },
      { value: 'AUDUSD', label: 'AUD/USD 🦘' },
      { value: 'USDCAD', label: 'USD/CAD 🍁' },
      { value: 'XAUUSD', label: 'Gold 🥇' },
      { value: 'SPX', label: 'S&P 500 📈' },
      { value: 'NDX', label: 'Nasdaq 💻' },
    ];
    
    function toggleSymbol(symbol) {
      const index = localSettings.watched_symbols.indexOf(symbol);
      if (index > -1) {
        localSettings.watched_symbols = localSettings.watched_symbols.filter(s => s !== symbol);
      } else {
        localSettings.watched_symbols = [...localSettings.watched_symbols, symbol];
      }
    }
    
    function saveSettings() {
      dispatch('update', {
        watched_symbols: localSettings.watched_symbols,
        alert_extreme: localSettings.alert_levels.extreme,
        alert_high: localSettings.alert_levels.high,
        alert_medium: localSettings.alert_levels.medium,
        discord_enabled: localSettings.channels.discord,
        telegram_enabled: localSettings.channels.telegram,
        custom_discord_webhook: localSettings.custom_webhooks.discord,
        quiet_hours_enabled: localSettings.quiet_hours.enabled,
        quiet_hours_start: localSettings.quiet_hours.start,
        quiet_hours_end: localSettings.quiet_hours.end,
        advance_notice_hours: localSettings.advanced.advance_notice_hours,
        min_expected_pips: localSettings.advanced.min_expected_pips,
        require_high_confidence: localSettings.advanced.require_high_confidence
      });
    }
  </script>
  
  <div class="config-container">
    <!-- Symboles Surveillés -->
    <section class="config-section">
      <h3>💱 Symboles Surveillés</h3>
      <p class="section-desc">Sélectionne les actifs pour lesquels tu veux recevoir des alertes</p>
      
      <div class="symbol-grid">
        {#each availableSymbols as sym}
          <label class="symbol-checkbox">
            <input 
              type="checkbox" 
              checked={localSettings.watched_symbols.includes(sym.value)}
              on:change={() => toggleSymbol(sym.value)}
            />
            <span class="checkbox-label">{sym.label}</span>
          </label>
        {/each}
      </div>
    </section>
    
    <!-- Niveaux d'Alerte -->
    <section class="config-section">
      <h3>⚠️ Niveaux d'Alerte</h3>
      <p class="section-desc">Choisis quels niveaux de risque doivent déclencher une alerte</p>
      
      <div class="toggle-list">
        <label class="toggle-item">
          <div class="toggle-info">
            <span class="toggle-label">🔴 Risque EXTRÊME</span>
            <span class="toggle-desc">Mouvements >20 pips attendus</span>
          </div>
          <input 
            type="checkbox" 
            bind:checked={localSettings.alert_levels.extreme}
            class="toggle"
          />
        </label>
        
        <label class="toggle-item">
          <div class="toggle-info">
            <span class="toggle-label">🟠 Risque ÉLEVÉ</span>
            <span class="toggle-desc">Mouvements 10-20 pips attendus</span>
          </div>
          <input 
            type="checkbox" 
            bind:checked={localSettings.alert_levels.high}
            class="toggle"
          />
        </label>
        
        <label class="toggle-item">
          <div class="toggle-info">
            <span class="toggle-label">🟡 Risque MODÉRÉ</span>
            <span class="toggle-desc">Mouvements 5-10 pips attendus</span>
          </div>
          <input 
            type="checkbox" 
            bind:checked={localSettings.alert_levels.medium}
            class="toggle"
          />
        </label>
      </div>
    </section>
    
    <!-- Canaux de Notification -->
    <section class="config-section">
      <h3>📢 Canaux de Notification</h3>
      <p class="section-desc">Active les plateformes sur lesquelles tu veux recevoir les alertes</p>
      
      <div class="toggle-list">
        <label class="toggle-item">
          <div class="toggle-info">
            <span class="toggle-label">💬 Discord</span>
            <span class="toggle-desc">Notifications via webhook Discord</span>
          </div>
          <input 
            type="checkbox" 
            bind:checked={localSettings.channels.discord}
            class="toggle"
          />
        </label>
        
        {#if localSettings.channels.discord}
          <div class="webhook-input">
            <label>
              <span>Webhook Discord personnalisé (optionnel)</span>
              <input 
                type="text" 
                bind:value={localSettings.custom_webhooks.discord}
                placeholder="https://discord.com/api/webhooks/..."
              />
            </label>
          </div>
        {/if}
        
        <label class="toggle-item">
          <div class="toggle-info">
            <span class="toggle-label">✈️ Telegram</span>
            <span class="toggle-desc">Notifications via bot Telegram</span>
          </div>
          <input 
            type="checkbox" 
            bind:checked={localSettings.channels.telegram}
            class="toggle"
          />
        </label>
      </div>
    </section>
    
    <!-- Heures de Silence -->
    <section class="config-section">
      <h3>🌙 Heures de Silence</h3>
      <p class="section-desc">Désactive les alertes pendant tes heures de sommeil</p>
      
      <label class="toggle-item">
        <div class="toggle-info">
          <span class="toggle-label">Activer heures de silence</span>
        </div>
        <input 
          type="checkbox" 
          bind:checked={localSettings.quiet_hours.enabled}
          class="toggle"
        />
      </label>
      
      {#if localSettings.quiet_hours.enabled}
        <div class="hours-input">
          <label>
            <span>Début (heure locale)</span>
            <input 
              type="number" 
              min="0" 
              max="23"
              bind:value={localSettings.quiet_hours.start}
            />
          </label>
          
          <label>
            <span>Fin (heure locale)</span>
            <input 
              type="number" 
              min="0" 
              max="23"
              bind:value={localSettings.quiet_hours.end}
            />
          </label>
        </div>
      {/if}
    </section>
    
    <!-- Paramètres Avancés -->
    <section class="config-section">
      <h3>⚙️ Paramètres Avancés</h3>
      
      <div class="advanced-inputs">
        <label>
          <span>⏰ Préavis (heures avant l'événement)</span>
          <input 
            type="number" 
            min="1" 
            max="24"
            bind:value={localSettings.advanced.advance_notice_hours}
          />
        </label>
        
        <label>
          <span>📏 Mouvement minimum requis (pips)</span>
          <input 
            type="number" 
            min="0" 
            step="0.5"
            bind:value={localSettings.advanced.min_expected_pips}
          />
        </label>
        
        <label class="toggle-item">
          <div class="toggle-info">
            <span class="toggle-label">Exiger confiance ÉLEVÉE uniquement</span>
            <span class="toggle-desc">Alertes seulement si ≥10 événements historiques</span>
          </div>
          <input 
            type="checkbox" 
            bind:checked={localSettings.advanced.require_high_confidence}
            class="toggle"
          />
        </label>
      </div>
    </section>
    
    <!-- Actions -->
    <div class="actions">
      <button class="save-btn" on:click={saveSettings}>
        💾 Enregistrer les Modifications
      </button>
      <button class="cancel-btn" on:click={() => localSettings = {...settings}}>
        ↩️ Annuler
      </button>
    </div>
  </div>
  
  <style>
    .config-container {
      max-width: 900px;
    }
    
    .config-section {
      background: white;
      padding: 2rem;
      border-radius: 12px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      margin-bottom: 2rem;
    }
    
    .config-section h3 {
      font-size: 1.3rem;
      color: #1e293b;
      margin-bottom: 0.5rem;
    }
    
    .section-desc {
      color: #64748b;
      font-size: 0.9rem;
      margin-bottom: 1.5rem;
    }
    
    /* Symbol Grid */
    .symbol-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 1rem;
    }
    
    .symbol-checkbox {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem;
      background: #f8fafc;
      border: 2px solid #e2e8f0;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
    }
    
    .symbol-checkbox:hover {
      border-color: #3b82f6;
      background: #eff6ff;
    }
    
    .symbol-checkbox input[type="checkbox"] {
      width: 20px;
      height: 20px;
      cursor: pointer;
    }
    
    .checkbox-label {
      font-weight: 600;
      color: #1e293b;
    }
    
    /* Toggle List */
    .toggle-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    
    .toggle-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.5rem;
      background: #f8fafc;
      border-radius: 8px;
      cursor: pointer;
    }
    
    .toggle-info {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }
    
    .toggle-label {
      font-weight: 600;
      color: #1e293b;
    }
    
    .toggle-desc {
      font-size: 0.85rem;
      color: #64748b;
    }
    
    .toggle {
      width: 50px;
      height: 28px;
      appearance: none;
      background: #cbd5e1;
      border-radius: 14px;
      position: relative;
      cursor: pointer;
      transition: background 0.2s;
    }
    
    .toggle:checked {
      background: #3b82f6;
    }
    
    .toggle::before {
      content: '';
      position: absolute;
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: white;
      top: 3px;
      left: 3px;
      transition: transform 0.2s;
    }
    
    .toggle:checked::before {
      transform: translateX(22px);
    }
    
    /* Inputs */
    .webhook-input,
    .hours-input,
    .advanced-inputs {
      margin-top: 1rem;
      padding: 1rem;
      background: #f8fafc;
      border-radius: 8px;
    }
    
    .webhook-input label,
    .hours-input label,
    .advanced-inputs label {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    
    .webhook-input span,
    .hours-input span,
    .advanced-inputs span {
      font-size: 0.9rem;
      font-weight: 600;
      color: #475569;
    }
    
    input[type="text"],
    input[type="number"] {
      padding: 0.75rem;
      border: 2px solid #e2e8f0;
      border-radius: 8px;
      font-size: 1rem;
      transition: border-color 0.2s;
    }
    
    input[type="text"]:focus,
    input[type="number"]:focus {
      outline: none;
      border-color: #3b82f6;
    }
    
    .hours-input {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }
    
    .advanced-inputs {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    
    /* Actions */
    .actions {
      display: flex;
      gap: 1rem;
      justify-content: flex-end;
    }
    
    .save-btn,
    .cancel-btn {
      padding: 1rem 2rem;
      border: none;
      border-radius: 8px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    
    .save-btn {
      background: #3b82f6;
      color: white;
    }
    
    .save-btn:hover {
      background: #2563eb;
      transform: translateY(-1px);
    }
    
    .cancel-btn {
      background: #f1f5f9;
      color: #475569;
    }
    
    .cancel-btn:hover {
      background: #e2e8f0;
    }
  </style>
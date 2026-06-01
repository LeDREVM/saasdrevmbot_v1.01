<script>
  /** @type {any} */
  export let userId;
  /** @type {any} */
  export let settings;
  
  let testStatus = '';
  let testing = false;
  
  const API_URL = 'http://localhost:8000/api';
  
  async function testDiscord() {
    if (!settings?.notifications?.discord_enabled) {
      testStatus = '❌ Discord non activé dans la configuration';
      return;
    }
    
    testing = true;
    testStatus = '⏳ Envoi du test Discord...';
    
    try {
      const response = await fetch(`${API_URL}/alert-config/test-notification/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel: 'discord' })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        testStatus = '✅ Test Discord envoyé avec succès !';
      } else {
        testStatus = `❌ Erreur: ${data.detail || 'Échec envoi'}`;
      }
    } catch (error) {
      testStatus = `❌ Erreur: ${error instanceof Error ? error.message : String(error)}`;
    } finally {
      testing = false;
      setTimeout(() => testStatus = '', 5000);
    }
  }

  async function testTelegram() {
    if (!settings?.notifications?.telegram_enabled) {
      testStatus = '❌ Telegram non activé dans la configuration';
      return;
    }
    
    testing = true;
    testStatus = '⏳ Envoi du test Telegram...';
    
    try {
      const response = await fetch(`${API_URL}/alert-config/test-notification/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel: 'telegram' })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        testStatus = '✅ Test Telegram envoyé avec succès !';
      } else {
        testStatus = `❌ Erreur: ${data.detail || 'Échec envoi'}`;
      }
    } catch (error) {
      testStatus = `❌ Erreur: ${error instanceof Error ? error.message : String(error)}`;
    } finally {
      testing = false;
      setTimeout(() => testStatus = '', 5000);
    }
  }
</script>

<div class="test-panel">
  <div class="test-buttons">
    <button 
      on:click={testDiscord} 
      disabled={testing || !settings?.notifications?.discord_enabled}
      class="test-btn discord">
      <span class="btn-icon">💬</span>
      <span>Test Discord</span>
    </button>
    
    <button 
      on:click={testTelegram} 
      disabled={testing || !settings?.notifications?.telegram_enabled}
      class="test-btn telegram">
      <span class="btn-icon">✈️</span>
      <span>Test Telegram</span>
    </button>
  </div>
  
  {#if testStatus}
    <div class="test-status" class:success={testStatus.includes('✅')} class:error={testStatus.includes('❌')}>
      {testStatus}
    </div>
  {/if}
  
  <div class="test-info">
    <p>💡 <strong>Astuce:</strong> Configure tes webhooks dans la section Configuration avant de tester.</p>
    
    <div class="channel-status">
      <div class="channel-item" class:enabled={settings?.notifications?.discord_enabled}>
        <span class="status-dot"></span>
        <span>Discord: {settings?.notifications?.discord_enabled ? 'Activé' : 'Désactivé'}</span>
      </div>
      
      <div class="channel-item" class:enabled={settings?.notifications?.telegram_enabled}>
        <span class="status-dot"></span>
        <span>Telegram: {settings?.notifications?.telegram_enabled ? 'Activé' : 'Désactivé'}</span>
      </div>
    </div>
  </div>
</div>

<style>
  .test-panel {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }
  
  .test-buttons {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }
  
  .test-btn {
    flex: 1;
    min-width: 200px;
    padding: 1.25rem 2rem;
    border: none;
    border-radius: 10px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
  }
  
  .test-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .test-btn.discord {
    background: #5865F2;
    color: white;
  }
  
  .test-btn.discord:hover:not(:disabled) {
    background: #4752C4;
    transform: translateY(-2px);
  }
  
  .test-btn.telegram {
    background: #0088cc;
    color: white;
  }
  
  .test-btn.telegram:hover:not(:disabled) {
    background: #006699;
    transform: translateY(-2px);
  }
  
  .btn-icon {
    font-size: 1.5rem;
  }
  
  .test-status {
    padding: 1rem;
    border-radius: 8px;
    text-align: center;
    font-weight: 600;
    animation: slideIn 0.3s ease-out;
  }
  
  .test-status.success {
    background: rgba(52, 211, 153, 0.12);
    color: var(--success);
    box-shadow: inset 0 0 0 1px rgba(52, 211, 153, 0.3);
  }

  .test-status.error {
    background: rgba(248, 113, 113, 0.12);
    color: var(--danger);
    box-shadow: inset 0 0 0 1px rgba(248, 113, 113, 0.3);
  }
  
  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  .test-info {
    background: var(--surface-2);
    border: 1px solid var(--border);
    padding: 1.5rem;
    border-radius: 8px;
    border-left: 4px solid var(--accent);
  }

  .test-info p {
    color: var(--text-muted);
    margin-bottom: 1rem;
  }

  .channel-status {
    display: flex;
    gap: 2rem;
  }

  .channel-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
    color: var(--text-muted);
  }

  .status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--text-dim);
  }

  .channel-item.enabled {
    color: var(--success);
    font-weight: 600;
  }

  .channel-item.enabled .status-dot {
    background: var(--success);
    box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.2);
  }
</style>

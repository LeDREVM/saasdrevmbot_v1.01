<script>
  import { onMount } from 'svelte';
  import TradingEconomicsWidget from './TradingEconomicsWidget.svelte';
  import TradingViewPanel from '$lib/components/TradingViewPanel.svelte';

  // Configuration de l'API (utilise l'env var ou localhost)
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

  let stats = {
    backend: { status: 'checking', url: API_URL },
    nextcloud: { status: 'checking' }
  };

  let currentFeature = 0;
  let isAnimating = false;

  const features = [
    {
      icon: '📅',
      title: 'Calendrier Économique',
      description: 'Événements en temps réel de ForexFactory et Investing.com',
      color: '#3b82f6',
      gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    },
    {
      icon: '🔔',
      title: 'Alertes Intelligentes',
      description: 'Notifications prédictives basées sur l\'historique',
      color: '#ef4444',
      gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
    },
    {
      icon: '📊',
      title: 'Analyse Statistique',
      description: 'Corrélation et impact des événements économiques',
      color: '#10b981',
      gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
    }
  ];

  const stats_data = [
    { label: 'Événements Analysés', value: '10,000+', icon: '📊' },
    { label: 'Alertes Envoyées', value: '5,000+', icon: '🔔' },
    { label: 'Précision', value: '95%', icon: '🎯' },
    { label: 'Uptime', value: '99.9%', icon: '⚡' }
  ];

  onMount(async () => {
    // Test backend
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`${API_URL}/health`, {
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (response.ok) {
        stats.backend.status = 'online';
      } else {
        stats.backend.status = 'offline';
      }
    } catch (error) {
      stats.backend.status = 'offline';
    }

    // Test Nextcloud
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`${API_URL}/api/nextcloud/status`, {
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        stats.nextcloud.status = data.connected ? 'connected' : 'disconnected';
      }
    } catch (error) {
      stats.nextcloud.status = 'error';
    }

    // Rotation automatique des features
    setInterval(() => {
      isAnimating = true;
      setTimeout(() => {
        currentFeature = (currentFeature + 1) % features.length;
        isAnimating = false;
      }, 300);
    }, 5000);
  });
</script>

<svelte:head>
  <title>saasDrevmBot — Trading Forex Intelligent</title>
  <meta name="description" content="Système d'alertes intelligent pour le trading Forex avec analyse du calendrier économique" />
</svelte:head>

<div class="home-container">
  <!-- Hero Section -->
  <header class="hero">
    <div class="hero-background">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
      <div class="gradient-orb orb-3"></div>
    </div>

    <div class="hero-content">
      <div class="hero-badge">
        <span class="badge-dot"></span>
        <span>Système en ligne · Version 2.0</span>
      </div>

      <h1 class="hero-title">
        <span class="gradient-text">SaaS DrevmBot</span>
      </h1>

      <p class="hero-subtitle">
        Système d'Alertes Intelligent pour le Trading Forex
      </p>

      <p class="hero-description">
        Analyse automatique du calendrier économique avec prédictions basées sur l'IA.
        Recevez des alertes en temps réel sur Discord et Telegram.
      </p>

      <div class="hero-cta">
        <a href="/calendar" class="btn btn-primary">
          <span>📅</span>
          <span>Voir le Calendrier</span>
        </a>
        <a href="/alerts" class="btn btn-secondary">
          <span>🔔</span>
          <span>Configurer les Alertes</span>
        </a>
      </div>
    </div>
  </header>

  <!-- Feature Showcase -->
  <section class="feature-showcase">
    <div class="showcase-card" class:animating={isAnimating}>
      <div class="showcase-icon" style="background: {features[currentFeature].gradient}">
        {features[currentFeature].icon}
      </div>
      <h3>{features[currentFeature].title}</h3>
      <p>{features[currentFeature].description}</p>
    </div>

    <div class="showcase-dots">
      {#each features as _, i}
        <button
          class="dot"
          class:active={i === currentFeature}
          on:click={() => { currentFeature = i; }}
          aria-label="Feature {i + 1}"
        ></button>
      {/each}
    </div>
  </section>

  <!-- Trading Dashboard : TradingView + Calendrier -->
  <section class="trading-dashboard">
    <div class="trading-grid">
      <div class="trading-grid-item">
        <TradingViewPanel />
      </div>
      <div class="trading-grid-item">
        <TradingEconomicsWidget />
      </div>
    </div>
  </section>

  <!-- Stats Section -->
  <section class="stats-section">
    <h2 class="section-title">📈 Performances en Temps Réel</h2>
    <div class="stats-grid">
      {#each stats_data as stat}
        <div class="stat-card">
          <div class="stat-icon">{stat.icon}</div>
          <div class="stat-value">{stat.value}</div>
          <div class="stat-label">{stat.label}</div>
        </div>
      {/each}
    </div>
  </section>

  <!-- Status Section -->
  <section class="status-section">
    <h2 class="section-title">🔧 Statut des Services</h2>

    <div class="status-grid">
      <div class="status-card {stats.backend.status}">
        <div class="status-header">
          <div class="status-icon-wrapper">
            {#if stats.backend.status === 'online'}
              <span class="status-icon pulse">✅</span>
            {:else if stats.backend.status === 'offline'}
              <span class="status-icon">❌</span>
            {:else}
              <span class="status-icon rotate">⏳</span>
            {/if}
          </div>
          <div class="status-info">
            <h3>Backend API</h3>
            <p class="status-url">{stats.backend.url}</p>
          </div>
        </div>
        <div class="status-badge {stats.backend.status}">
          {stats.backend.status === 'online' ? '🟢 En ligne' : stats.backend.status === 'offline' ? '🔴 Hors ligne' : '🟡 Vérification...'}
        </div>
      </div>

      <div class="status-card {stats.nextcloud.status}">
        <div class="status-header">
          <div class="status-icon-wrapper">
            {#if stats.nextcloud.status === 'connected'}
              <span class="status-icon pulse">✅</span>
            {:else if stats.nextcloud.status === 'disconnected'}
              <span class="status-icon">⚠️</span>
            {:else if stats.nextcloud.status === 'error'}
              <span class="status-icon">❌</span>
            {:else}
              <span class="status-icon rotate">⏳</span>
            {/if}
          </div>
          <div class="status-info">
            <h3>Nextcloud Sync</h3>
            <p class="status-url">ledream.kflw.io</p>
          </div>
        </div>
        <div class="status-badge {stats.nextcloud.status}">
          {stats.nextcloud.status === 'connected' ? '🟢 Connecté' : stats.nextcloud.status === 'disconnected' ? '🟠 Déconnecté' : stats.nextcloud.status === 'error' ? '🔴 Erreur' : '🟡 Vérification...'}
        </div>
      </div>
    </div>
  </section>

  <!-- Features Grid -->
  <section class="features-section">
    <h2 class="section-title">🚀 Fonctionnalités Principales</h2>

    <div class="features-grid">
      <a href="/calendar" class="feature-card">
        <div class="feature-icon-bg" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)">
          <div class="feature-icon">📅</div>
        </div>
        <h3>Calendrier Économique</h3>
        <p>Événements en temps réel de ForexFactory et Investing.com avec filtrage par impact</p>
        <div class="feature-arrow">→</div>
      </a>

      <a href="/stats" class="feature-card">
        <div class="feature-icon-bg" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)">
          <div class="feature-icon">📊</div>
        </div>
        <h3>Statistiques Avancées</h3>
        <p>Analyse de corrélation, impact des événements et historique des mouvements de prix</p>
        <div class="feature-arrow">→</div>
      </a>

      <a href="/alerts" class="feature-card">
        <div class="feature-icon-bg" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%)">
          <div class="feature-icon">🔔</div>
        </div>
        <h3>Alertes Intelligentes</h3>
        <p>Notifications prédictives sur Discord et Telegram basées sur l'historique</p>
        <div class="feature-arrow">→</div>
      </a>
    </div>
  </section>

  <!-- Quick Links -->
  <section class="quick-links">
    <h2 class="section-title">🔗 Accès Rapide</h2>

    <div class="links-grid">
      <a href="{API_URL}/api/docs" target="_blank" rel="noopener noreferrer" class="link-card">
        <span class="link-icon">📚</span>
        <div class="link-content">
          <span class="link-title">API Documentation</span>
          <span class="link-desc">Swagger UI</span>
        </div>
        <span class="link-external">↗</span>
      </a>

      <a href="https://ledream.kflw.io/apps/files/?dir=/ForexBot" target="_blank" rel="noopener noreferrer" class="link-card">
        <span class="link-icon">☁️</span>
        <div class="link-content">
          <span class="link-title">Nextcloud Files</span>
          <span class="link-desc">Rapports & Exports</span>
        </div>
        <span class="link-external">↗</span>
      </a>

      <a href="{API_URL}/health" target="_blank" rel="noopener noreferrer" class="link-card">
        <span class="link-icon">❤️</span>
        <div class="link-content">
          <span class="link-title">Health Check</span>
          <span class="link-desc">API Status</span>
        </div>
        <span class="link-external">↗</span>
      </a>

      <a href="https://github.com/yourusername/saasDrevmbot" target="_blank" rel="noopener noreferrer" class="link-card">
        <span class="link-icon">💻</span>
        <div class="link-content">
          <span class="link-title">GitHub Repository</span>
          <span class="link-desc">Source Code</span>
        </div>
        <span class="link-external">↗</span>
      </a>
    </div>
  </section>

  <!-- Footer -->
  <footer class="footer">
    <p>
      <strong>SaaS DrevmBot</strong> - Système d'Alertes Intelligent pour le Trading Forex
    </p>
    <p class="footer-links">
      <a href="https://saasdrevmbot.netlify.app/">🌐 Site Web</a>
      <span>•</span>
      <a href="{API_URL}/api/docs">📚 API Docs</a>
      <span>•</span>
      <a href="https://github.com/yourusername/saasDrevmbot">💻 GitHub</a>
    </p>
    <p class="footer-copyright">
      © 2026 DrevmBot. Déployé sur <a href="https://netlify.com" target="_blank" rel="noopener noreferrer">Netlify</a>
    </p>
  </footer>
</div>

<style>
  .home-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
    min-height: 100vh;
  }

  /* Hero Section */
  .hero {
    position: relative;
    background:
      radial-gradient(120% 120% at 0% 0%, rgba(99, 102, 241, 0.35) 0%, transparent 55%),
      radial-gradient(120% 120% at 100% 100%, rgba(34, 211, 238, 0.25) 0%, transparent 55%),
      var(--surface-solid);
    color: var(--text);
    padding: 5rem 3rem;
    border-radius: var(--radius-lg);
    margin-bottom: 4rem;
    overflow: hidden;
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
  }

  .hero-background {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    overflow: hidden;
    opacity: 0.5;
  }

  .gradient-orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(90px);
    animation: float 20s infinite ease-in-out;
  }

  .orb-1 {
    width: 400px;
    height: 400px;
    background: #6366f1;
    top: -200px;
    left: -100px;
  }

  .orb-2 {
    width: 300px;
    height: 300px;
    background: #22d3ee;
    bottom: -150px;
    right: -50px;
    animation-delay: -5s;
  }

  .orb-3 {
    width: 250px;
    height: 250px;
    background: #a855f7;
    top: 50%;
    right: 20%;
    animation-delay: -10s;
  }

  @keyframes float {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(30px, -30px) scale(1.1); }
    66% { transform: translate(-20px, 20px) scale(0.9); }
  }

  .hero-content {
    position: relative;
    z-index: 1;
    text-align: center;
    max-width: 800px;
    margin: 0 auto;
  }

  .hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    background: rgba(255, 255, 255, 0.06);
    backdrop-filter: blur(10px);
    padding: 0.5rem 1rem;
    border-radius: 50px;
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 2rem;
    border: 1px solid var(--border-strong);
    color: var(--text-muted);
  }

  .badge-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--success);
    box-shadow: 0 0 10px var(--success);
    animation: pulse 2s infinite;
  }

  .hero-title {
    font-size: 4rem;
    font-weight: 900;
    margin-bottom: 1rem;
    line-height: 1.1;
    letter-spacing: -0.03em;
  }

  .gradient-text {
    background: linear-gradient(135deg, #c7d2fe 0%, #22d3ee 60%, #a855f7 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .hero-subtitle {
    font-size: 1.7rem;
    margin-bottom: 1rem;
    color: var(--text);
    font-weight: 700;
  }

  .hero-description {
    font-size: 1.1rem;
    color: var(--text-muted);
    line-height: 1.6;
    margin-bottom: 2.5rem;
  }

  .hero-cta {
    display: flex;
    gap: 1rem;
    justify-content: center;
    flex-wrap: wrap;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 1rem 2rem;
    border-radius: var(--radius-sm);
    font-size: 1.05rem;
    font-weight: 700;
    text-decoration: none;
    transition: all 0.3s;
    cursor: pointer;
    border: 1px solid transparent;
  }

  .btn-primary {
    background: var(--accent-grad);
    color: #fff;
    box-shadow: 0 10px 30px rgba(34, 211, 238, 0.3);
  }

  .btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 14px 36px rgba(34, 211, 238, 0.45);
  }

  .btn-secondary {
    background: rgba(255, 255, 255, 0.05);
    color: var(--text);
    backdrop-filter: blur(10px);
    border: 1px solid var(--border-strong);
  }

  .btn-secondary:hover {
    border-color: var(--accent);
    color: var(--accent);
    transform: translateY(-2px);
  }

  /* Feature Showcase */
  .feature-showcase {
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 3rem;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    margin-bottom: 4rem;
    text-align: center;
    backdrop-filter: blur(12px);
  }

  .showcase-card {
    transition: all 0.3s;
  }

  .showcase-card.animating {
    opacity: 0;
    transform: translateY(10px);
  }

  .showcase-icon {
    width: 120px;
    height: 120px;
    margin: 0 auto 1.5rem;
    border-radius: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 4rem;
    box-shadow: 0 18px 40px rgba(0, 0, 0, 0.4);
  }

  .showcase-card h3 {
    font-size: 2rem;
    color: var(--text);
    margin-bottom: 1rem;
  }

  .showcase-card p {
    font-size: 1.1rem;
    color: var(--text-muted);
    max-width: 600px;
    margin: 0 auto;
  }

  .showcase-dots {
    display: flex;
    gap: 0.75rem;
    justify-content: center;
    margin-top: 2rem;
  }

  .dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--border-strong);
    border: none;
    cursor: pointer;
    transition: all 0.3s;
    padding: 0;
  }

  .dot.active {
    background: var(--accent);
    width: 32px;
    border-radius: 6px;
    box-shadow: 0 0 12px var(--accent);
  }

  /* Stats Section */
  .stats-section {
    margin-bottom: 4rem;
  }

  .section-title {
    font-size: 2rem;
    color: var(--text);
    margin-bottom: 2rem;
    font-weight: 800;
    text-align: center;
    letter-spacing: -0.02em;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
  }

  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 2rem;
    border-radius: var(--radius);
    box-shadow: var(--shadow-sm);
    text-align: center;
    transition: all 0.3s;
    backdrop-filter: blur(12px);
  }

  .stat-card:hover {
    transform: translateY(-4px);
    border-color: var(--border-strong);
    box-shadow: var(--shadow);
  }

  .stat-icon {
    font-size: 2.5rem;
    margin-bottom: 1rem;
  }

  .stat-value {
    font-size: 2.5rem;
    font-weight: 900;
    font-family: var(--font-mono);
    background: var(--accent-grad);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.5rem;
  }

  .stat-label {
    font-size: 0.95rem;
    color: var(--text-muted);
    font-weight: 600;
  }

  /* Status Section */
  .status-section {
    margin-bottom: 4rem;
  }

  .status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
  }

  .status-card {
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 2rem;
    border-radius: var(--radius);
    box-shadow: var(--shadow-sm);
    border-left: 3px solid var(--border-strong);
    transition: all 0.3s;
    backdrop-filter: blur(12px);
  }

  .status-card:hover {
    transform: translateX(4px);
    box-shadow: var(--shadow);
  }

  .status-card.online,
  .status-card.connected {
    border-left-color: var(--success);
    background: linear-gradient(135deg, rgba(52, 211, 153, 0.08) 0%, var(--surface) 60%);
  }

  .status-card.offline,
  .status-card.error {
    border-left-color: var(--danger);
    background: linear-gradient(135deg, rgba(248, 113, 113, 0.08) 0%, var(--surface) 60%);
  }

  .status-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .status-icon-wrapper {
    font-size: 2.5rem;
  }

  .status-icon.pulse {
    animation: pulse 2s infinite;
  }

  .status-icon.rotate {
    animation: rotate 2s linear infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  @keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .status-info h3 {
    font-size: 1.3rem;
    color: var(--text);
    margin-bottom: 0.25rem;
    font-weight: 700;
  }

  .status-url {
    font-size: 0.85rem;
    color: var(--text-dim);
    font-family: var(--font-mono);
  }

  .status-badge {
    display: inline-block;
    padding: 0.5rem 1rem;
    border-radius: 8px;
    font-size: 0.9rem;
    font-weight: 700;
    background: var(--surface-2);
    color: var(--text-muted);
    border: 1px solid var(--border);
  }

  /* Features Grid */
  .features-section {
    margin-bottom: 4rem;
  }

  .features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 2rem;
  }

  .feature-card {
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 2.5rem;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    text-decoration: none;
    color: inherit;
    transition: all 0.3s;
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(12px);
  }

  .feature-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--accent-grad);
    transform: scaleX(0);
    transition: transform 0.3s;
    transform-origin: left;
  }

  .feature-card:hover::before {
    transform: scaleX(1);
  }

  .feature-card:hover {
    transform: translateY(-8px);
    border-color: var(--border-strong);
    box-shadow: var(--shadow);
  }

  .feature-icon-bg {
    width: 80px;
    height: 80px;
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1.5rem;
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
  }

  .feature-icon {
    font-size: 2.5rem;
  }

  .feature-card h3 {
    font-size: 1.5rem;
    color: var(--text);
    margin-bottom: 1rem;
    font-weight: 700;
  }

  .feature-card p {
    color: var(--text-muted);
    font-size: 1rem;
    line-height: 1.6;
    margin-bottom: 1rem;
  }

  .feature-arrow {
    font-size: 1.5rem;
    color: var(--accent);
    font-weight: 700;
  }

  /* Quick Links */
  .quick-links {
    margin-bottom: 4rem;
  }

  .links-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.5rem;
  }

  .link-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.5rem;
    background: var(--surface);
    border-radius: var(--radius);
    text-decoration: none;
    color: var(--text);
    transition: all 0.3s;
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--border);
    backdrop-filter: blur(12px);
  }

  .link-card:hover {
    border-color: var(--accent);
    transform: translateX(4px);
    box-shadow: var(--glow);
  }

  .link-icon {
    font-size: 2rem;
    flex-shrink: 0;
  }

  .link-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .link-title {
    font-weight: 700;
    font-size: 1.05rem;
  }

  .link-desc {
    font-size: 0.85rem;
    color: var(--text-dim);
  }

  .link-external {
    font-size: 1.5rem;
    color: var(--accent);
    flex-shrink: 0;
  }

  /* Trading Dashboard */
  .trading-dashboard {
    margin: 3rem 0;
  }

  .trading-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr);
    gap: 1.5rem;
    align-items: stretch;
  }

  .trading-grid-item {
    min-width: 0;
  }

  /* Footer */
  .footer {
    text-align: center;
    padding: 3rem 2rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    color: var(--text-muted);
    backdrop-filter: blur(12px);
  }

  .footer strong {
    color: var(--text);
  }

  .footer p {
    margin: 0.5rem 0;
  }

  .footer-links {
    display: flex;
    gap: 1rem;
    justify-content: center;
    align-items: center;
    flex-wrap: wrap;
  }

  .footer-links a {
    color: var(--accent);
    text-decoration: none;
    font-weight: 600;
    transition: color 0.2s;
  }

  .footer-links a:hover {
    color: var(--accent-3);
  }

  .footer-copyright {
    font-size: 0.9rem;
    margin-top: 1rem;
    color: var(--text-dim);
  }

  .footer-copyright a {
    color: var(--accent);
    text-decoration: none;
    font-weight: 600;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .home-container {
      padding: 1rem;
    }

    .hero {
      padding: 3rem 2rem;
    }

    .hero-title {
      font-size: 2.5rem;
    }

    .hero-subtitle {
      font-size: 1.3rem;
    }

    .hero-cta {
      flex-direction: column;
    }

    .btn {
      width: 100%;
      justify-content: center;
    }

    .feature-showcase {
      padding: 2rem;
    }

    .showcase-icon {
      width: 80px;
      height: 80px;
      font-size: 3rem;
    }

    .stats-grid {
      grid-template-columns: repeat(2, 1fr);
    }

    .trading-grid {
      grid-template-columns: 1fr;
    }
  }
</style>

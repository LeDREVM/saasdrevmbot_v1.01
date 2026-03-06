<script>
  import { onMount } from 'svelte';
  import TradingEconomicsWidget from './TradingEconomicsWidget.svelte';
  
  // Configuration de l'API (utilise l'env var ou localhost)
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  
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
        <span class="badge-icon">🚀</span>
        <span>Nouvelle Version 2.0</span>
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

  <!-- Trading Economics Widget -->
  <section class="trading-economics-section">
    <TradingEconomicsWidget />
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
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: #f8fafc;
  }

  .home-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
    min-height: 100vh;
  }

  /* Hero Section */
  .hero {
    position: relative;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 5rem 3rem;
    border-radius: 24px;
    margin-bottom: 4rem;
    overflow: hidden;
    box-shadow: 0 20px 60px rgba(102, 126, 234, 0.4);
  }

  .hero-background {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    overflow: hidden;
    opacity: 0.3;
  }

  .gradient-orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    animation: float 20s infinite ease-in-out;
  }

  .orb-1 {
    width: 400px;
    height: 400px;
    background: #f093fb;
    top: -200px;
    left: -100px;
  }

  .orb-2 {
    width: 300px;
    height: 300px;
    background: #4facfe;
    bottom: -150px;
    right: -50px;
    animation-delay: -5s;
  }

  .orb-3 {
    width: 250px;
    height: 250px;
    background: #43e97b;
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
    gap: 0.5rem;
    background: rgba(255, 255, 255, 0.2);
    backdrop-filter: blur(10px);
    padding: 0.5rem 1rem;
    border-radius: 50px;
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 2rem;
    border: 1px solid rgba(255, 255, 255, 0.3);
  }

  .badge-icon {
    font-size: 1.2rem;
  }

  .hero-title {
    font-size: 4rem;
    font-weight: 900;
    margin-bottom: 1rem;
    line-height: 1.1;
  }

  .gradient-text {
    background: linear-gradient(135deg, #ffffff 0%, #f0f0f0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .hero-subtitle {
    font-size: 1.8rem;
    margin-bottom: 1rem;
    opacity: 0.95;
    font-weight: 600;
  }

  .hero-description {
    font-size: 1.1rem;
    opacity: 0.85;
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
    border-radius: 12px;
    font-size: 1.1rem;
    font-weight: 700;
    text-decoration: none;
    transition: all 0.3s;
    cursor: pointer;
    border: none;
  }

  .btn-primary {
    background: white;
    color: #667eea;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  }

  .btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
  }

  .btn-secondary {
    background: rgba(255, 255, 255, 0.2);
    color: white;
    backdrop-filter: blur(10px);
    border: 2px solid rgba(255, 255, 255, 0.3);
  }

  .btn-secondary:hover {
    background: rgba(255, 255, 255, 0.3);
    transform: translateY(-2px);
  }

  /* Feature Showcase */
  .feature-showcase {
    background: white;
    padding: 3rem;
    border-radius: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    margin-bottom: 4rem;
    text-align: center;
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
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  }

  .showcase-card h3 {
    font-size: 2rem;
    color: #1e293b;
    margin-bottom: 1rem;
  }

  .showcase-card p {
    font-size: 1.1rem;
    color: #64748b;
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
    background: #e2e8f0;
    border: none;
    cursor: pointer;
    transition: all 0.3s;
    padding: 0;
  }

  .dot.active {
    background: #667eea;
    width: 32px;
    border-radius: 6px;
  }

  /* Stats Section */
  .stats-section {
    margin-bottom: 4rem;
  }

  .section-title {
    font-size: 2rem;
    color: #1e293b;
    margin-bottom: 2rem;
    font-weight: 800;
    text-align: center;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
  }

  .stat-card {
    background: white;
    padding: 2rem;
    border-radius: 16px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
    text-align: center;
    transition: all 0.3s;
  }

  .stat-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.12);
  }

  .stat-icon {
    font-size: 2.5rem;
    margin-bottom: 1rem;
  }

  .stat-value {
    font-size: 2.5rem;
    font-weight: 900;
    color: #667eea;
    margin-bottom: 0.5rem;
  }

  .stat-label {
    font-size: 0.95rem;
    color: #64748b;
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
    background: white;
    padding: 2rem;
    border-radius: 16px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
    border-left: 4px solid #e2e8f0;
    transition: all 0.3s;
  }

  .status-card:hover {
    transform: translateX(4px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  }

  .status-card.online,
  .status-card.connected {
    border-left-color: #10b981;
    background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%);
  }

  .status-card.offline,
  .status-card.error {
    border-left-color: #ef4444;
    background: linear-gradient(135deg, #ffffff 0%, #fef2f2 100%);
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
    color: #1e293b;
    margin-bottom: 0.25rem;
    font-weight: 700;
  }

  .status-url {
    font-size: 0.85rem;
    color: #64748b;
    font-family: 'Courier New', monospace;
  }

  .status-badge {
    display: inline-block;
    padding: 0.5rem 1rem;
    border-radius: 8px;
    font-size: 0.9rem;
    font-weight: 700;
    background: #f1f5f9;
    color: #64748b;
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
    background: white;
    padding: 2.5rem;
    border-radius: 20px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
    text-decoration: none;
    color: inherit;
    transition: all 0.3s;
    position: relative;
    overflow: hidden;
  }

  .feature-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #667eea, #764ba2);
    transform: scaleX(0);
    transition: transform 0.3s;
  }

  .feature-card:hover::before {
    transform: scaleX(1);
  }

  .feature-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.15);
  }

  .feature-icon-bg {
    width: 80px;
    height: 80px;
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
  }

  .feature-icon {
    font-size: 2.5rem;
  }

  .feature-card h3 {
    font-size: 1.5rem;
    color: #1e293b;
    margin-bottom: 1rem;
    font-weight: 700;
  }

  .feature-card p {
    color: #64748b;
    font-size: 1rem;
    line-height: 1.6;
    margin-bottom: 1rem;
  }

  .feature-arrow {
    font-size: 1.5rem;
    color: #667eea;
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
    background: white;
    border-radius: 12px;
    text-decoration: none;
    color: #1e293b;
    transition: all 0.3s;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
    border: 2px solid transparent;
  }

  .link-card:hover {
    border-color: #667eea;
    transform: translateX(4px);
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2);
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
    color: #64748b;
  }

  .link-external {
    font-size: 1.5rem;
    color: #667eea;
    flex-shrink: 0;
  }

  /* Footer */
  .trading-economics-section {
    margin: 3rem 0;
  }

  .footer {
    text-align: center;
    padding: 3rem 2rem;
    background: white;
    border-radius: 20px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
    color: #64748b;
  }

  .footer strong {
    color: #1e293b;
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
    color: #667eea;
    text-decoration: none;
    font-weight: 600;
    transition: color 0.2s;
  }

  .footer-links a:hover {
    color: #764ba2;
  }

  .footer-copyright {
    font-size: 0.9rem;
    margin-top: 1rem;
  }

  .footer-copyright a {
    color: #667eea;
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
  }
</style>

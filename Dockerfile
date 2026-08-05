# ============================================================
# Serveur Express — hub GoldyXbOT + dashboard /correlations
# Sert : / (hub), /dashboard, /correlations, /api/stats/correlations
# Port 3000. Puppeteer N'est PAS requis ici (géré par screenshot-service).
# ============================================================
FROM node:18-alpine

WORKDIR /app

# Dépendances de prod uniquement (express, socket.io, node-cron,
# yahoo-finance2, discord.js, cheerio, axios, dotenv…)
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Code + données seed (events_log.json pour le moteur de corrélation)
COPY src ./src
COPY data ./data

ENV PORT=3000
EXPOSE 3000

CMD ["node", "src/server.js"]

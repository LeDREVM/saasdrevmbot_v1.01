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

# Code + données seed. Le seed est copié HORS du point de montage du volume
# (/app/data-seed) ; l'entrypoint alimente /app/data si le volume est vierge,
# pour ne pas perdre events_log.json quand un volume nommé masque l'image.
COPY src ./src
COPY data ./data-seed
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENV PORT=3000
EXPOSE 3000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["node", "src/server.js"]

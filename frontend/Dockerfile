FROM node:18-alpine

WORKDIR /app

# Copier package.json et package-lock.json
COPY package*.json ./

# Installer les dépendances
RUN npm install

# Copier le code
COPY . .

# Exposer le port
EXPOSE 5173

# Commande par défaut
CMD ["npm", "run", "dev", "--", "--host"]

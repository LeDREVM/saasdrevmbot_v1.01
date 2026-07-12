#!/bin/bash

# Script de déploiement Netlify pour SaaS DrevmBot
# Usage: ./deploy-netlify.sh

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║   🚀 DÉPLOIEMENT NETLIFY - SaaS DrevmBot 🚀           ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
print_step() {
    echo -e "${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

# Vérifier si on est dans le bon répertoire
if [ ! -d "frontend" ]; then
    print_error "Le dossier 'frontend' n'existe pas. Êtes-vous dans le bon répertoire ?"
    exit 1
fi

print_success "Répertoire du projet trouvé"

# Vérifier si Node.js est installé
if ! command -v node &> /dev/null; then
    print_error "Node.js n'est pas installé. Installez-le depuis https://nodejs.org/"
    exit 1
fi

print_success "Node.js $(node -v) détecté"

# Vérifier si npm est installé
if ! command -v npm &> /dev/null; then
    print_error "npm n'est pas installé"
    exit 1
fi

print_success "npm $(npm -v) détecté"

# Se déplacer dans le dossier frontend
cd frontend

# Vérifier si package.json existe
if [ ! -f "package.json" ]; then
    print_error "package.json n'existe pas dans le dossier frontend"
    exit 1
fi

print_success "package.json trouvé"

# Installer les dépendances
print_step "Installation des dépendances..."
npm install
print_success "Dépendances installées"

# Vérifier si .env existe, sinon créer depuis env.template
if [ ! -f ".env" ]; then
    if [ -f "env.template" ]; then
        print_warning ".env n'existe pas, création depuis env.template..."
        cp env.template .env
        print_success ".env créé depuis env.template"
        print_warning "⚠️  N'oubliez pas de configurer VITE_API_URL dans .env ou dans Netlify !"
    else
        print_warning ".env n'existe pas. Les variables d'environnement doivent être configurées dans Netlify."
    fi
fi

# Build de production
print_step "Build de production..."
npm run build

if [ $? -eq 0 ]; then
    print_success "Build réussi !"
else
    print_error "Le build a échoué"
    exit 1
fi

# Vérifier si le dossier build existe
if [ ! -d "build" ]; then
    print_error "Le dossier 'build' n'a pas été créé"
    exit 1
fi

print_success "Dossier build créé"

# Vérifier si Netlify CLI est installé
if ! command -v netlify &> /dev/null; then
    print_warning "Netlify CLI n'est pas installé"
    echo ""
    echo "Pour déployer, vous avez 2 options :"
    echo ""
    echo "1️⃣  Installer Netlify CLI et déployer :"
    echo "   npm install -g netlify-cli"
    echo "   netlify login"
    echo "   netlify deploy --prod"
    echo ""
    echo "2️⃣  Déployer manuellement :"
    echo "   - Aller sur https://app.netlify.com/"
    echo "   - Glisser-déposer le dossier 'frontend/build'"
    echo ""
    echo "3️⃣  Déployer via Git (Recommandé) :"
    echo "   - Pusher le code sur GitHub/GitLab"
    echo "   - Connecter le repo à Netlify"
    echo "   - Netlify déploiera automatiquement"
    echo ""
    exit 0
fi

print_success "Netlify CLI détecté"

# Demander confirmation pour le déploiement
echo ""
echo "═══════════════════════════════════════════════════════"
echo "🚀 Prêt à déployer sur Netlify !"
echo "═══════════════════════════════════════════════════════"
echo ""
read -p "Voulez-vous déployer maintenant ? (o/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[OoYy]$ ]]; then
    print_step "Déploiement en cours..."
    
    # Déploiement de production
    netlify deploy --prod
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "╔════════════════════════════════════════════════════════╗"
        echo "║   ✅ DÉPLOIEMENT RÉUSSI ! ✅                          ║"
        echo "╚════════════════════════════════════════════════════════╝"
        echo ""
        print_success "Site déployé sur : https://saasdrevmbot.netlify.app/"
        echo ""
        echo "📋 Prochaines étapes :"
        echo "  1. Vérifier le site en production"
        echo "  2. Configurer VITE_API_URL dans Netlify (si pas fait)"
        echo "  3. Déployer le backend"
        echo "  4. Tester les fonctionnalités"
        echo ""
    else
        print_error "Le déploiement a échoué"
        exit 1
    fi
else
    echo ""
    print_warning "Déploiement annulé"
    echo ""
    echo "Pour déployer plus tard, exécutez :"
    echo "  cd frontend"
    echo "  netlify deploy --prod"
    echo ""
fi

cd ..

echo "═══════════════════════════════════════════════════════"
echo "✨ Script terminé avec succès !"
echo "═══════════════════════════════════════════════════════"

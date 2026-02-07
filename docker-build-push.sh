#!/bin/bash

# Script de build et push des images Docker vers Docker Hub
# Repository: ledrevm/goldyxrodgersbot

set -e

# Variables
DOCKER_USERNAME="ledrevm"
IMAGE_NAME="goldyxrodgersbot"
VERSION="1.0.0"
LATEST_TAG="latest"

echo "🐳 Build et Push Docker Images"
echo "================================"
echo "Repository: $DOCKER_USERNAME/$IMAGE_NAME"
echo "Version: $VERSION"
echo ""

# Vérifier si connecté à Docker Hub
echo "📝 Vérification connexion Docker Hub..."
if ! docker info | grep -q "Username: $DOCKER_USERNAME"; then
    echo "⚠️  Non connecté à Docker Hub"
    echo "Connexion..."
    docker login
fi

echo "✅ Connecté à Docker Hub"
echo ""

# Build Backend
echo "🔨 Build Backend Image..."
docker build -t $DOCKER_USERNAME/$IMAGE_NAME:backend-$VERSION ./backend
docker tag $DOCKER_USERNAME/$IMAGE_NAME:backend-$VERSION $DOCKER_USERNAME/$IMAGE_NAME:backend-$LATEST_TAG

echo "✅ Backend image built"
echo ""

# Build Frontend
echo "🔨 Build Frontend Image..."
docker build -t $DOCKER_USERNAME/$IMAGE_NAME:frontend-$VERSION ./frontend
docker tag $DOCKER_USERNAME/$IMAGE_NAME:frontend-$VERSION $DOCKER_USERNAME/$IMAGE_NAME:frontend-$LATEST_TAG

echo "✅ Frontend image built"
echo ""

# Push Backend
echo "📤 Push Backend Image..."
docker push $DOCKER_USERNAME/$IMAGE_NAME:backend-$VERSION
docker push $DOCKER_USERNAME/$IMAGE_NAME:backend-$LATEST_TAG

echo "✅ Backend image pushed"
echo ""

# Push Frontend
echo "📤 Push Frontend Image..."
docker push $DOCKER_USERNAME/$IMAGE_NAME:frontend-$VERSION
docker push $DOCKER_USERNAME/$IMAGE_NAME:frontend-$LATEST_TAG

echo "✅ Frontend image pushed"
echo ""

# Build et Push image complète (optionnel)
echo "🔨 Build Complete Image..."
docker build -t $DOCKER_USERNAME/$IMAGE_NAME:$VERSION .
docker tag $DOCKER_USERNAME/$IMAGE_NAME:$VERSION $DOCKER_USERNAME/$IMAGE_NAME:$LATEST_TAG

echo "📤 Push Complete Image..."
docker push $DOCKER_USERNAME/$IMAGE_NAME:$VERSION
docker push $DOCKER_USERNAME/$IMAGE_NAME:$LATEST_TAG

echo ""
echo "✅ Toutes les images ont été poussées avec succès !"
echo ""
echo "Images disponibles:"
echo "  - $DOCKER_USERNAME/$IMAGE_NAME:backend-$VERSION"
echo "  - $DOCKER_USERNAME/$IMAGE_NAME:backend-$LATEST_TAG"
echo "  - $DOCKER_USERNAME/$IMAGE_NAME:frontend-$VERSION"
echo "  - $DOCKER_USERNAME/$IMAGE_NAME:frontend-$LATEST_TAG"
echo "  - $DOCKER_USERNAME/$IMAGE_NAME:$VERSION"
echo "  - $DOCKER_USERNAME/$IMAGE_NAME:$LATEST_TAG"
echo ""
echo "Pour utiliser:"
echo "  docker pull $DOCKER_USERNAME/$IMAGE_NAME:backend-$LATEST_TAG"
echo "  docker pull $DOCKER_USERNAME/$IMAGE_NAME:frontend-$LATEST_TAG"

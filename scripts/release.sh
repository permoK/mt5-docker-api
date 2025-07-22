#!/bin/bash
# Script para crear releases

set -e

# Check if version argument provided
if [ $# -eq 0 ]; then
    echo "Usage: ./scripts/release.sh <version>"
    echo "Example: ./scripts/release.sh 1.0.0"
    exit 1
fi

VERSION=$1

# Validate version format
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must be in format X.Y.Z (e.g., 1.0.0)"
    exit 1
fi

echo "Creating release v$VERSION..."

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "Error: Releases must be created from main branch"
    echo "Current branch: $CURRENT_BRANCH"
    exit 1
fi

# Check if working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: Working directory has uncommitted changes"
    git status --short
    exit 1
fi

# Pull latest changes
echo "Pulling latest changes..."
git pull origin main

# Create and push tag
echo "Creating tag v$VERSION..."
git tag -a "v$VERSION" -m "Release version $VERSION"

echo "Pushing tag to remote..."
git push origin "v$VERSION"

echo "✅ Release v$VERSION created successfully!"
echo ""
echo "The GitHub Actions workflow will now:"
echo "1. Run tests"
echo "2. Build Docker image"
echo "3. Push to Docker Hub with tags: latest, $VERSION, ${VERSION%.*}, ${VERSION%%.*}"
echo "4. Create GitHub release"
echo ""
echo "Check progress at: https://github.com/jefrnc/mt5-docker-api/actions"
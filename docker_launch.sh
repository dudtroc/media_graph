#!/bin/bash

# Default mode is build
mode="nothing"
clean_build=false

# Parse command-line options
while getopts "brcd" opt; do
  case $opt in
    b)
      mode="build"
      ;;
    r)
      mode="run"
      ;;
    c)
      clean_build=true
      ;;
    d)
      mode="stop"
      ;;
    *)
      echo "Invalid option: -$OPTARG >&2"
      exit 1
      ;;
  esac
done

# Check if the chosen mode is supported
if [ "$mode" != "build" ] && [ "$mode" != "run" ] && [ "$mode" != "stop" ]; then
  echo "Unsupported mode use ['-b' / '-r' / '-d']" >&2
  exit 1
fi

# Execute the corresponding docker command based on the chosen mode
if [ "$mode" == "build" ]; then
  # Clean build option: remove existing images and containers
  if [ "$clean_build" == true ]; then
    echo "Cleaning existing Docker images and containers..."
    
    # Stop and remove containers using the image
    docker ps -a --filter ancestor=media-graph:1.0 -q | xargs -r docker rm -f
    
    # Remove the image
    docker rmi -f media-graph:1.0 2>/dev/null || true
    
    # Clean up dangling images and containers
    docker system prune -f
    
    echo "Cleanup completed."
  fi
  
  # Build all Docker images
  echo "Building all Docker images..."
  
  # Build main media-graph image
  echo "Building media-graph:1.0..."
  docker build -t media-graph:1.0 -f ./docker/Dockerfile .
  
  # Build all services with docker-compose (no-cache to ensure fresh build)
  echo "Building all services with docker-compose..."
  docker-compose build --no-cache
  
  echo "All Docker images built successfully!"
  
elif [ "$mode" == "run" ]; then
  # Run with Docker Compose (RabbitMQ + Redis + API + Celery Worker)
  echo "Starting Media Graph services with Docker Compose..."
  echo "This will start:"
  echo "  - RabbitMQ (port 5673, management UI: 15673)"
  echo "  - Redis (port 6380)"
  echo "  - API Server (port 10105)"
  echo "  - Celery Worker"
  echo ""
  echo "To access RabbitMQ management UI: http://localhost:15673 (admin/admin123)"
  echo "To access API: http://localhost:10105"
  echo ""
  
  # Docker Compose로 모든 서비스 시작 (빌드 없이)
  docker-compose up --no-build

elif [ "$mode" == "stop" ]; then
  # Stop all running Docker services
  echo "Stopping Media Graph services..."
  echo "This will stop:"
  echo "  - RabbitMQ"
  echo "  - Redis" 
  echo "  - API Server"
  echo "  - Celery Worker"
  echo ""
  
  # Stop docker-compose services first
  echo "Stopping docker-compose services..."
  docker-compose down 2>/dev/null || echo "No docker-compose services running or already stopped"
  
  # Stop containers by their specific names (more reliable)
  echo "Stopping containers by name..."
  
  # Stop and remove specific containers
  for container_name in "media-graph-rabbitmq" "media-graph-redis" "media-graph-api" "media-graph-celery-worker"; do
    if docker ps -q -f name=$container_name | grep -q .; then
      echo "Stopping $container_name..."
      docker stop $container_name 2>/dev/null || true
      docker rm $container_name 2>/dev/null || true
    else
      echo "$container_name is not running"
    fi
  done
  
  # Also stop any containers using the media-graph images (fallback)
  echo "Stopping any remaining containers using media-graph images..."
  docker ps -a --filter ancestor=media-graph-api -q | xargs -r docker stop 2>/dev/null || true
  docker ps -a --filter ancestor=media-graph-api -q | xargs -r docker rm -f 2>/dev/null || true
  docker ps -a --filter ancestor=media-graph-celery-worker -q | xargs -r docker stop 2>/dev/null || true
  docker ps -a --filter ancestor=media-graph-celery-worker -q | xargs -r docker rm -f 2>/dev/null || true
  
  echo "All Media Graph services have been stopped."
fi
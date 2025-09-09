#!/bin/bash

# Default mode is build
mode="nothing"
clean_build=false

# Parse command-line options
while getopts "brc" opt; do
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
    *)
      echo "Invalid option: -$OPTARG >&2"
      exit 1
      ;;
  esac
done

# Check if the chosen mode is supported
if [ "$mode" != "build" ] && [ "$mode" != "run" ]; then
  echo "Unsupported mode use ['-b' / '-r']" >&2
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
  
  # Build the Docker image
  echo "Building Docker image..."
  docker build -t media-graph:1.0 -f ./docker/Dockerfile .
  echo "Docker image built successfully!"
  
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
  
  # Docker Compose로 모든 서비스 시작
  docker-compose up
fi
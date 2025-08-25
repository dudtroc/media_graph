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
  # Run the Docker container
  xhost +
  # docker run --gpus all -it --rm -p 10102:10102 -v $(pwd):/media-benchmark -e DISPLAY=$DISPLAY media-benchmark:1.0
  #docker run --gpus all -it --rm -v $(pwd):/workspace -v /media/ktva/DATA10TB/kt_benchmark:/workspace/data -e DISPLAY=$DISPLAY media-shot-detect:1.0
  # docker run --gpus all -it --rm -p 10102:10102 -v $(pwd):/workspace -v /media/ktva/DATA10TB:/workspace/data --net=host -e DISPLAY=$DISPLAY media-graph:1.0
  
  # RetrievalGraphConverter에서 사용하는 경로들을 마운트
  # - /home/ktva/PROJECT/Diffusion/GP_adapter/output -> /workspace/diffusion_data/output
  # - /home/ktva/PROJECT/Diffusion/GP_adapter/cache -> /workspace/diffusion_data/cache
  docker run --gpus all -it --rm -p 10102:10102 \
    -v $(pwd):/workspace \
    -v /home/ktva/PROJECT/Diffusion/GP_adapter/output:/media_data/output \
    -v /home/ktva/PROJECT/Diffusion/GP_adapter/cache:/media_data/cache \
    --net=host \
    -e DISPLAY=$DISPLAY \
    media-graph:1.0
  
  # Execute the run command
  # ...
fi
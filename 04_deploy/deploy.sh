#!/bin/bash

while [[ $# -gt 0 ]]; do
    case $1 in
        --build-base)
            BUILD_BASE=true
            shift
            ;;
        --test-deploy)
            TEST_DEPLOY=true
            shift
            ;;
        --cluster-deploy)
            CLUSTER_DEPLOY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

#setting up the deployment mode for the aggregator and orchestrator
if [ "$TEST_DEPLOY" = true ]; then
    echo "Preparing for test deploy mode"
    python3 deployment_setter.py --test-deploy
elif [ "$CLUSTER_DEPLOY" = true ]; then
    echo "Preparing for cluster deploy mode"
    python3 deployment_setter.py --cluster-deploy
else
    echo "Preparing for default (test) deploy mode"
    python3 deployment_setter.py --test-deploy
fi

#building the images
if [ "$BUILD_BASE" = true ]; then
    ./build_images.sh --build-base
else
    ./build_images.sh
fi

#deploying the stack
if [ "$TEST_DEPLOY" = true ]; then
    echo "Deploying in test deploy mode"
    docker compose up
elif [ "$CLUSTER_DEPLOY" = true ]; then
    echo "Deploying in cluster deploy mode"
    if [ "$BUILD_BASE" = true ]; then
        ./publish_images_to_github.sh --build
    else
        ./publish_images_to_github.sh
    fi
else
    echo "Deploying in default deploy mode"
    docker compose up --add-host=host-gateway
fi

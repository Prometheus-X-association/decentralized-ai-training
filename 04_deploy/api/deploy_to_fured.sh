#!/bin/bash

Help()
{
    echo "Deploying BB01 API to fured.cloud"
    echo 
    echo "Syntax: deploy_to_fured.sh <port> <password>"
    echo "options:"
    echo "-h     Print this Help."
    echo
}

while getopts ":h" option; do
    case $option in
        h) # display Help
            Help
            exit;;
        \?) # Invalid option
            echo "Error: Invalid option"
            exit;;
    esac
done

echo Publishing to vm.fured.cloud:$1

sshpass -p $2 scp -o StrictHostKeyChecking=no -P $1 -r ./* cloud@vm.fured.cloud.bme.hu:/home/cloud/bb01_api

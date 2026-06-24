#!/bin/bash

echo Publishing to vm.fured.cloud:$1

sshpass -p $2 scp -o StrictHostKeyChecking=no -P $1 -r ./ cloud@vm.fured.cloud.bme.hu:/home/cloud/bb01_api

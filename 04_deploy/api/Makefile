# Copyright 2026 Janos Czentye
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
CREDS := exchange.env
DOCK_COMP := docker compose -f ${ROOT_DIR}/docker-compose.yaml --env-file=${ROOT_DIR}/creds/${CREDS}

########################################################################################################################

build ::
	./setup_pdc.sh
	${DOCK_COMP} build

setup ::
	${DOCK_COMP} up --force-recreate --abort-on-container-exit

setup-all ::
	${DOCK_COMP} --profile extra up --force-recreate --abort-on-container-exit

restart :: | teardown setup

########################################################################################################################

exchange ::
	./test_exchange.sh

config ::
	./test_config.sh

credential ::
	./test_credential.sh

########################################################################################################################

status ::
	${DOCK_COMP} ps -a

teardown ::
	${DOCK_COMP} --profile extra down -v

########################################################################################################################

SHELL := bash
.SILENT:	# Set silent mode (-s) by default
.DEFAULT_GOAL := setup

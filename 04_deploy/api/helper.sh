#!/usr/bin/env bash
# Copyright 2025 Janos Czentye
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

_RED='\033[1;31m'
_GREEN='\033[0;32m'
_YELLOW='\033[1;33m'
_NC='\033[0m' # No Color

function LOG() {
    printf -v sep '%*s' 80 ""; echo -e "\n${sep// /#}"
    echo "###   $1"
    printf -v sep '%*s' 80 ""; echo -e "${sep// /#}\n"
}

function log() {
    echo -e "\n$1"
    printf -v sep '%*s' 80 ""; echo -e "${sep// /-}\n"
}

function warning() {
    printf -v sep '%*s' 80 ""; echo -e "\n${_YELLOW}${sep// /-}"
    echo "### [WARNING]   $1"
    printf -v sep '%*s' 80 ""; echo -e "${sep// /-}${_NC}\n"
}

function error() {
    printf -v sep '%*s' 80 ""; echo -e "\n${_RED}${sep// /#}"
    echo "### [ERROR]   $1"
    printf -v sep '%*s' 80 ""; echo -e "${sep// /#}${_NC}\n"
}

function _timeout() {
    # Example: _timeout 5 longrunning_command args
    # Example: { _timeout 5 producer || echo KABOOM $?; } | consumer
    # Example: producer | { _timeout 5 consumer1; consumer2; }
    # Example: { while date; do sleep .3; done; } | _timeout 5 cat | less
    # - Needs Bash 4.3 for wait -n
    # - Gives 137 if the command was killed, else the return value of the command.
    # - Works for pipes. (You do not need to go foreground here!)
    # - Works with internal shell commands or functions, too.
    ( set +b; sleep "$1" & "${@:2}" & wait -n; r=$?; kill -9 "$(jobs -p)"; exit $r; )
}

function wait_enter() {
    echo -e "\n\n" && read -rp ">>> Press ENTER to continue ${1}..."
}
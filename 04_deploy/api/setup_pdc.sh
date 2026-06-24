#!/usr/bin/env bash
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
set -euo pipefail

source "$(readlink -f "$(dirname "$0")/helper.sh")"

########################################################################################################################

PDC_REPO=https://github.com/Prometheus-X-association/dataspace-connector.git
PDC_VERSION="1.10.1"
PDC_IMG="dataspace-connector"
#PDC_DIR="${HOME}/pdc"

########################################################################################################################

LOG "Setup Dataspace Connector (PDC)"

if [ -z "${PDC_DIR:-}" ]; then
    PDC_DIR=$(readlink -f "$(dirname "$0")/pdc")
fi
rm -rf "${PDC_DIR}" && mkdir -vp "${PDC_DIR}"
echo "Used dir for PDC: ${PDC_DIR}"

log "Pull PDC source with version: ${PDC_VERSION}..."
git clone "${PDC_REPO}" "${PDC_DIR}"
pushd "${PDC_DIR}"
    git switch --detach "v${PDC_VERSION}"
popd

########################################################################################################################

log "Adjust docker setup..."
cat <<'EOF' >"${PDC_DIR}/docker/app/Dockerfile"
# Use the official Node.js image as base image
FROM node:22
ARG ENV
ENV ENV=$ENV

# Install pnpm globally
RUN npm install -g pnpm@9.15.5

# Create app directory
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY package.json .

## Bundle app source
COPY . .

RUN chmod +x ./docker/scripts/start.sh

RUN rm -f node_modules
RUN rm -f /src/logs

RUN mkdir -p /src/logs
RUN mkdir -p /src/keys

# Install app dependencies
RUN pnpm install --frozen-lockfile --ignore-scripts

# Expose the port on which the app will run
EXPOSE 3000

CMD ["./docker/scripts/start.sh", "$ENV"]
EOF
ls -alht "${PDC_DIR}/docker/app/Dockerfile"

log "Create config files..."
cat <<EOF >"${PDC_DIR}/src/config.json"
{
    "endpoint": "",
    "serviceKey": "",
    "secretKey": "",
    "catalogUri": "",
    "contractUri": "",
    "consentUri": "",
    "credentials": [],
    "expressLimitSize": "",
    "serviceChainAdapter": false,
    "serviceChainAdapterTimeout": 0
}
EOF
ls -alht "${PDC_DIR}/src/config.json"

cat <<EOF >"${PDC_DIR}/.env"
NODE_ENV=production
PORT=3000

SESSION_SECRET=$(openssl rand -base64 32 | tr -d /=+ | cut -c -16)
SESSION_COOKIE_EXPIRATION=24000

MONGO_URI=
MONGO_INITDB_ROOT_USERNAME=
MONGO_INITDB_ROOT_PASSWORD=

# Logs
WINSTON_LOGS_MAX_FILES=14d
WINSTON_LOGS_MAX_SIZE=20m

#jwt
JWT_BEARER_TOKEN_EXPIRATION=3h
JWT_REFRESH_TOKEN_EXPIRATION=1d

# Exchange Trigger
EXCHANGE_TRIGGER_API_KEY=

# Exchange Timeout in seconds
EXCHANGE_TIMEOUT=120
EOF
ls -alht "${PDC_DIR}/.env"

########################################################################################################################

log "Build PDC..."
docker build -f "${PDC_DIR}/docker/app/Dockerfile" \
             -t "${PDC_IMG}:${PDC_VERSION}" \
             -t "${PDC_IMG}:latest" \
             --build-arg "ENV=production" \
             --pull \
             "${PDC_DIR}"

docker images -f "reference=*dataspace-connector*" --no-trunc

########################################################################################################################

echo -e "\nDone."
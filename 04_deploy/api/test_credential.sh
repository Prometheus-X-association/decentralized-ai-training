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
source "$(readlink -f "$(dirname "$0")/creds/exchange.env")"

########################################################################################################################

LOG "Test Credential"

log "Initiate login..."
LOGIN_BODY=$(jq -n "$(cat <<EOF
{
    "secretKey": "${PDC_SECRET_KEY}",
    "serviceKey": "${PDC_SERVICE_KEY}"
}
EOF
)")

_URL="https://${NGROK_DOMAIN}/login"
echo "Used URL: ${_URL}"

echo -e "\nPrepared login body:"
echo "${LOGIN_BODY}" | jq

RESP=$(curl -Ssf -X POST \
                "${_URL}" \
                -H "Content-Type: application/json" \
                -d "${LOGIN_BODY}")

echo -e "\nReceived response:"
echo "${RESP}" | jq

if [ "$(jq '.code' <<<"${RESP}")" -ne 200 ]; then
    error "Login request failed!" && exit 1
else
    TOKEN=$(jq -r '.content.token' <<<"${RESP}")
    echo "${TOKEN}" >creds/consumer.login.token
    echo -e "\nLogin was successful!"
fi

echo -e "\nBearer token: ${TOKEN}"

########################################################################################################################

log "Register credential..."

CREDENTIAL_BODY=$(jq -n "$(cat <<EOF
{
    "type": "api-key",
    "key": "Bearer",
    "value": "xxx"
}
EOF
)")

_URL="https://${NGROK_DOMAIN}/private/credentials"
echo "Used URL: ${_URL}"

echo -e "\nPrepared credential body:"
echo "${CREDENTIAL_BODY}" | jq

RESP=$(curl -Ssf -X POST \
                "${_URL}" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer ${TOKEN}" \
                -d "${CREDENTIAL_BODY}")

echo -e "\nReceived response:"
echo "${RESP}" | jq

if [ "$(jq '.code' <<<"${RESP}")" -ne 201 ]; then
    error "Credential request failed!" && exit 1
else
    CRED_ID=$(jq -r '.content._id' <<<"${RESP}")
    echo "${CRED_ID}" >creds/credential.id
    echo -e "\nCredential registration was successful!"
fi

echo -e "\nCredential ID: ${CRED_ID}"

########################################################################################################################

log "Validate PDC configuration..."

_URL="https://${NGROK_DOMAIN}/private/credentials"
echo -e "\nUsed URL: ${_URL}"

RESP=$(curl -Ssf -X GET \
                "${_URL}" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer ${TOKEN}")

echo -e "\nReceived response:"
echo "${RESP}" | jq

if [ "$(jq '.code' <<<"${RESP}")" -ne 200 ]; then
    error "Config config failed!" && exit 1
else
    echo -e "\nConfig validation was successful!"
fi

########################################################################################################################

echo -e "\nDone."
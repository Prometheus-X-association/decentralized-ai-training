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

LOG "Test Exchange"

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

log "Initiate consumer exchange for descriptor (JSON)..."

echo "Used consumer parameter: ${PARAM=$(date +%s)}"
EXCHANGE_BODY=$(jq -n "$(cat <<EOF
{
    "contract": "https://contract.visionstrust.com/contracts/${CONTRACT_ID}",
    "purposeId": "https://api.visionstrust.com/v1/catalog/serviceofferings/${CONSUMER_OFFER_ID}",
    "resourceId": "https://api.visionstrust.com/v1/catalog/serviceofferings/${PROVIDER_OFFER_ID}",
    "resources": [
        {
            "resource": "https://api.visionstrust.com/v1/catalog/dataresources/${PROVIDER_RESOURCE_ID}",
            "params": {
                "query": [
                    {
                        "test": "true"
                    },
                    {
                        "param": "${PARAM}"
                    }
                ]
            }
        }
    ],
    "purposes": [
        {
             "resource": "https://api.visionstrust.com/v1/catalog/softwareresources/${CONSUMER_RESOURCE_ID}"
        }
    ],
    "consumerParams": {
        "query": [
            {
                "test": "true"
            }
        ]
    }
}
EOF
)")

_URL="https://${NGROK_DOMAIN}/consumer/exchange"
echo "Used URL: ${_URL}"

echo -e "\nPrepared exchange body:"
echo "${EXCHANGE_BODY}" | jq

RESP=$(curl -s -X POST \
                "${_URL}" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer ${TOKEN}" \
                -d "${EXCHANGE_BODY}")

echo -e "\nReceived response:"
echo "${RESP}" | jq

if [ "$(jq '.code' <<<"${RESP}")" -ne 200 ] || [ "$(jq '.content.success' <<<"${RESP}")" != "true" ]; then
    error "Exchange request failed!" && exit 1
else
    echo -e "\nConsumer exchange was successful!"
fi

echo -e "\nExchange status: $(jq -r '.content.dataExchange.status' <<<"${RESP}")"

########################################################################################################################

echo -e "\nDone."
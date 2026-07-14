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
#

set -euo pipefail

#source "$(readlink -f "$(dirname "$0")/creds/exchange.env")"


echo "Initiate login..."
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
                -d "${LOGIN_BODY}" \
                --max-time 30)

echo -e "\nReceived response:"
echo "${RESP}" | jq

if [ "$(jq '.code' <<<"${RESP}")" -ne 200 ]; then
    echo "Login request failed!" && exit 1
else
    TOKEN=$(jq -r '.content.token' <<<"${RESP}")
    #echo "${TOKEN}" >creds/consumer.login.token
    echo -e "\nLogin was successful!"
fi

export PDC_TOKEN=${TOKEN}

echo -e "\nBearer token: ${TOKEN}"

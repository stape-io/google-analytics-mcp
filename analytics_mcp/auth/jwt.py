# Copyright 2026 Stape
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime as dt
import logging
from typing import Any

from joserfc import jwk, jwt

logger = logging.getLogger(__name__)


class JWTProvider:
    private_keys: jwk.KeySet
    algorithm: str
    issuer: str
    audience: str
    subject: str
    scopes: list[str]
    token_lifetime: dt.timedelta

    def __init__(
        self,
        private_keys: jwk.KeySet,
        algorithm: str,
        claims: dict[str, Any],
        token_lifetime: dt.timedelta = dt.timedelta(minutes=1),
    ) -> None:
        self.private_keys = private_keys
        self.algorithm = algorithm
        self.token_lifetime = token_lifetime
        self.claims = claims

    def __call__(self) -> str:
        issued_at = dt.datetime.now()
        expiration_time = issued_at + self.token_lifetime

        claims = self.claims.copy()
        claims.update(
            {
                "iat": int(issued_at.timestamp()),
                "exp": int(expiration_time.timestamp()),
                "nbf": int(issued_at.timestamp()),
            }
        )

        logger.debug("Generating JWT with claims", extra={"claims": claims})
        try:
            token = jwt.encode(
                header={"alg": self.algorithm},
                claims=claims,
                key=self.private_keys,
                algorithms=[self.algorithm],
            )
            return token
        except Exception as e:
            logger.error(
                "Failed to generate JWT", extra={"error": str(e)}, exc_info=e
            )
            raise

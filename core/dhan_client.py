from __future__ import annotations

from typing import Any

import requests

from core.config import get_settings


class DhanHttpError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        path: str,
        message: str,
        response_text: str = "",
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.path = path
        self.response_text = response_text
        self.payload = payload or {}


class DhanClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.timeout = self.settings.timeout_seconds
        self.base_url = "https://api.dhan.co"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "access-token": self.settings.dhan_access_token,
            "client-id": self.settings.dhan_client_id,
        }

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"

        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Dhan request failed before response | path={path} | error={exc}") from exc

        response_text = response.text[:5000]

        if not response.ok:
            raise DhanHttpError(
                status_code=response.status_code,
                path=path,
                message=(
                    f"Dhan HTTP error | status={response.status_code} | "
                    f"path={path} | response={response_text}"
                ),
                response_text=response_text,
                payload=payload,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"Dhan returned non-JSON response | path={path} | body={response_text}"
            ) from exc

        if not isinstance(data, dict):
            raise RuntimeError(f"Expected dict response from Dhan, got: {type(data)} | path={path}")

        return data

    def get_ltp(
        self,
        security_ids: list[int | str],
        exchange_segment: str = "NSE_EQ",
    ) -> dict[str, Any]:
        normalized_ids: list[int] = []

        for x in security_ids:
            text = str(x).strip()
            if not text:
                continue
            try:
                normalized_ids.append(int(text))
            except ValueError as exc:
                raise ValueError(f"Invalid security ID for Dhan LTP request: {x}") from exc

        if not normalized_ids:
            return {"data": {}, "status": "success"}

        payload = {
            exchange_segment: normalized_ids
        }

        return self._post("/v2/marketfeed/ltp", payload)

    def get_option_chain(
        self,
        underlying_scrip: int,
        underlying_seg: str,
        expiry: str,
    ) -> dict[str, Any]:
        payload = {
            "UnderlyingScrip": underlying_scrip,
            "UnderlyingSeg": underlying_seg,
            "Expiry": expiry,
        }
        return self._post("/v2/optionchain", payload)

    def get_expiry_list(self, underlying_scrip: int, underlying_seg: str) -> dict[str, Any]:
        payload = {
            "UnderlyingScrip": underlying_scrip,
            "UnderlyingSeg": underlying_seg,
        }
        return self._post("/v2/optionchain/expirylist", payload)
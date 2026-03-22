from __future__ import annotations

from typing import Any

import requests

from core.config import get_settings


class SupabaseHttpError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        method: str,
        path: str,
        message: str,
        response_text: str = "",
        payload: Any = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.method = method
        self.path = path
        self.response_text = response_text
        self.payload = payload
        self.params = params or {}


class SupabaseClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.supabase_url.rstrip("/")
        self.timeout = self.settings.timeout_seconds
        self.headers = {
            "apikey": self.settings.supabase_service_role_key,
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/rest/v1/{path.lstrip('/')}"

    def _normalize_filter_value(self, value: Any) -> str:
        if isinstance(value, str) and (
            value.startswith("eq.")
            or value.startswith("neq.")
            or value.startswith("gt.")
            or value.startswith("gte.")
            or value.startswith("lt.")
            or value.startswith("lte.")
            or value.startswith("like.")
            or value.startswith("ilike.")
            or value.startswith("in.")
            or value.startswith("is.")
        ):
            return value
        return f"eq.{value}"

    def _normalize_order(self, order: str, ascending: bool) -> str:
        raw = str(order).strip()
        lower = raw.lower()

        if lower.endswith(".asc") or lower.endswith(".desc"):
            return raw

        direction = "asc" if ascending else "desc"
        return f"{raw}.{direction}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_payload: Any = None,
    ) -> Any:
        url = self._url(path)
        final_headers = headers or self.headers

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=final_headers,
                params=params,
                json=json_payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Supabase request failed before response | method={method} | path={path} | error={exc}"
            ) from exc

        response_text = response.text[:5000]

        if not response.ok:
            raise SupabaseHttpError(
                status_code=response.status_code,
                method=method,
                path=path,
                message=(
                    f"Supabase HTTP error | status={response.status_code} | "
                    f"method={method} | path={path} | params={params or {}} | "
                    f"response={response_text}"
                ),
                response_text=response_text,
                payload=json_payload,
                params=params,
            )

        if not response.text.strip():
            return None

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"Supabase returned non-JSON response | method={method} | path={path} | body={response_text}"
            ) from exc

    def select(
        self,
        table: str,
        columns: str = "*",
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order: str | None = None,
        ascending: bool = True,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "select": columns,
        }

        if filters:
            for key, value in filters.items():
                params[key] = self._normalize_filter_value(value)

        if order:
            params["order"] = self._normalize_order(order, ascending)

        if limit is not None:
            params["limit"] = str(limit)

        if offset is not None:
            params["offset"] = str(offset)

        data = self._request(
            "GET",
            table,
            headers=self.headers,
            params=params,
        )

        if not isinstance(data, list):
            raise RuntimeError(f"Expected list response from Supabase select, got: {type(data)}")

        return data

    def insert(self, table: str, rows: list[dict[str, Any]] | dict[str, Any]) -> Any:
        return self._request(
            "POST",
            table,
            headers=self.headers,
            json_payload=rows,
        )

    def upsert(
        self,
        table: str,
        rows: list[dict[str, Any]] | dict[str, Any],
        on_conflict: str | None = None,
    ) -> Any:
        headers = dict(self.headers)
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"

        params: dict[str, Any] = {}
        if on_conflict:
            params["on_conflict"] = on_conflict

        return self._request(
            "POST",
            table,
            headers=headers,
            params=params,
            json_payload=rows,
        )

    def rpc(
        self,
        fn_name: str | None = None,
        payload: dict[str, Any] | None = None,
        *,
        function_name: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        actual_fn_name = function_name or fn_name
        actual_payload = params if params is not None else payload

        if not actual_fn_name:
            raise ValueError("rpc() requires fn_name or function_name")

        return self._request(
            "POST",
            f"rpc/{actual_fn_name}",
            headers=self.headers,
            json_payload=actual_payload or {},
        )

    def delete(self, table: str, filters: dict[str, Any] | None = None) -> Any:
        params: dict[str, Any] = {}

        if filters:
            for key, value in filters.items():
                params[key] = self._normalize_filter_value(value)

        return self._request(
            "DELETE",
            table,
            headers=self.headers,
            params=params,
        )
"""Construcción segura de URL RTSP (LOOP-0013-HOTFIX).

Responsabilidad única: componer una URL RTSP a partir de campos
separados (host, usuario, contraseña) percent-codificando las
credenciales, sin exponerlas en ninguna representación persistente.

La contraseña solo existe en la URL resultante en memoria. Ninguna
función de este módulo imprime, loguea ni persiste la URL completa con
credenciales; para representaciones legibles se usa
`redact_rtsp_url()` de `src.observability.logging_setup`.
"""

from urllib.parse import quote, urlsplit, urlunsplit


def build_rtsp_url(host: str, username: str, password: str) -> str:
    """Construye una URL RTSP con credenciales percent-codificadas.

    - host: URL base RTSP sin credenciales (p. ej.
      `rtsp://192.168.1.50:554/cam/realmonitor?channel=1&subtype=1`).
    - username: usuario RTSP (puede estar vacío).
    - password: contraseña RTSP (puede estar vacía).

    Si no hay usuario ni contraseña, devuelve el host tal cual.
    Devuelve cadena vacía si host no está definido.
    """
    host = (host or "").strip()
    if not host:
        return ""
    if not username and not password:
        return host

    parts = urlsplit(host)
    user = quote(username or "", safe="")
    pwd = quote(password or "", safe="")
    if pwd:
        netloc = f"{user}:{pwd}@{parts.netloc}"
    else:
        netloc = f"{user}@{parts.netloc}"
    return urlunsplit(
        (parts.scheme, netloc, parts.path, parts.query, parts.fragment)
    )

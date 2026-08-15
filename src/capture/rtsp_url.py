"""Construcción segura de URL RTSP (LOOP-0013-HOTFIX, LOOP-0014-HOTFIX).

Responsabilidad única: componer una URL RTSP a partir de campos
separados (host, usuario, contraseña, canal, subtype) percent-codificando las
credenciales, sin exponerlas en ninguna representación persistente.

La contraseña solo existe en la URL resultante en memoria. Ninguna
función de este módulo imprime, loguea ni persiste la URL completa con
credenciales; para representaciones legibles se usa
`redact_rtsp_url()` de `src.observability.logging_setup`.
"""

from urllib.parse import quote, urlsplit, urlunsplit, parse_qsl, urlencode


def build_rtsp_url(
    host: str,
    username: str = "",
    password: str = "",
    channel: int = 1,
    subtype: int = 1,
) -> str:
    """Construye una URL RTSP con credenciales percent-codificadas.

    - host: URL base RTSP sin credenciales (p. ej.
      `rtsp://192.168.1.50:554/cam/realmonitor`).
    - username: usuario RTSP (puede estar vacío).
    - password: contraseña RTSP (puede estar vacía).
    - channel: número de canal (1-16, por defecto 1).
    - subtype: tipo de stream (1 por defecto, main/substream).

    Normalización de ruta (LOOP-0015-FIX): si `host` no trae ruta
    (`rtsp://HOST` o `rtsp://HOST:554`), se completa automáticamente
    `/cam/realmonitor` antes de la query. Si ya contiene `/cam/realmonitor`
    no se duplica. Si trae una ruta explícita diferente, se preserva tal cual.

    Si no hay usuario ni contraseña, devuelve el host con query params.
    Devuelve cadena vacía si host no está definido.
    """
    host = (host or "").strip()
    if not host:
        return ""
    if not host.startswith("rtsp://"):
        return ""

    parts = urlsplit(host)
    user = quote(username or "", safe="")
    pwd = quote(password or "", safe="")
    if pwd:
        netloc = f"{user}:{pwd}@{parts.netloc}"
    else:
        netloc = f"{user}@{parts.netloc}" if user else parts.netloc

    # Normalización de ruta Dahua RTSP (LOOP-0015-FIX)
    path = parts.path
    if not path or path == "/":
        path = "/cam/realmonitor"

    # Build query parameters with channel and subtype
    query_params = parse_qsl(parts.query, keep_blank_values=True)
    query_dict = dict(query_params)
    query_dict["channel"] = str(channel)
    query_dict["subtype"] = str(subtype)
    new_query = urlencode(query_dict)

    return urlunsplit(
        (parts.scheme, netloc, path, new_query, parts.fragment)
    )


RTSP_SUBTYPE = "FIXED_1"
"""Diagnóstico de conexión RTSP de TukeVision.

Responsabilidad única: validar una URL RTSP proporcionada explícitamente
y devolver un resultado estructurado inmutable, sin descubrir streams,
sin construir credenciales, sin ejecutar detección ni negocio.

Reutiliza `RTSPSource` existente. No crea implementación paralela de
captura RTSP.
"""

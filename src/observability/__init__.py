"""Observabilidad de TukeVision.

Responsabilidad única: registrar la ejecución local y exponer un health
check operativo sin alterar la lógica del núcleo certificado. Incluye:

- Logging a archivo (logging estándar) con RUN_ID por ejecución y
  redacción de credenciales.
- Diagnóstico local de configuración, modelo, fuente, disco y evidencia.
"""

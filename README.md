# TukeVision — Centro de Mando & Inteligencia Visual Gobernada

TukeVision es una plataforma de software para centros de comando de videovigilancia, analítica de comportamiento retail y prevención de pérdidas en tiempo real. Opera bajo una arquitectura **local-first** en hardware estándar (CPU x86_64, Windows/Linux), sin requerir servidores en la nube ni conexión obligatoria a internet.

---

## 1. Capacidades Principales del Producto

### 1.1 Monitoreo Multicámara en Vivo (HD Focus & Cuadrículas Dinámicas)
- Ingesta simultánea de hasta 16 cámaras concurrentes (RTSP H.264/H.265 o archivos locales).
- Cuadrículas simétricas automáticas: 1, 4, 6 (1 principal + 5 auxiliares), 9 y 16 cámaras.
- Modo **Foco HD**: Ampliación con preservación de resolución nativa (1080p/4K), zoom digital interactivo (1x a 4x) y HUD técnico con separación explícita de `FUENTE`, `PRESENTACIÓN` e `INFERENCIA`.
- **Panel Técnico Colapsable**: El panel lateral es colapsable bajo demanda (`Detalles Técnicos`), maximizando el área útil de video al 80-100% de la pantalla.

### 1.2 Inferencia Visual Edge & Cascada de Inteligencia
- Aceleración en el borde mediante OpenVINO (CPU/iGPU/GPU) con fallback automático.
- Cascada estructurada: Detección de Movimiento → Inferencia Edge → ByteTrack → Análisis Temporal de Permanencia → Evaluación de Políticas Gobernadas.

### 1.3 Cero Inteligencia Fabricada (Zero Fake Data)
- Todo dato visible es `HECHO (FACT)` verificado físicamente, `INFERENCIA (INFERENCE)` determinista o `DESCONOCIDO (UNKNOWN)`.
- Eliminación total de alarmas sintéticas generadas por capas visuales: el rastreo puro no genera situaciones falsas (`DETECTION != TRACK != SITUATION`).

### 1.4 Bóveda de Evidencia Forense & Preparación para Firma ONVIF
- Empaquetado atómico de clips de video MP4 (PyAV) con cuadros clave y metadatos sidecar JSON.
- Integridad local garantizada mediante hashes criptográficos SHA-256 inmutables.
- Trazabilidad de origen y preparación para firma de medios ONVIF (`FUENTE NO FIRMADA (DVR LOCAL)` para DVRs estándar).
- Búsqueda estructurada SQLite e indexación con enlaces directos de origen (`dvr://`).

### 1.5 Interfaz de Usuario Unificada en Español (`es-CL`)
- Vistas operacionales integradas:
  - 📊 **RESUMEN**: Panel ejecutivo con métricas en vivo, situaciones activas y cola de atención.
  - 📹 **EN VIVO**: Cuadrícula de cámaras con interacción en tiempo real y panel técnico colapsable.
  - ⚠️ **SITUACIONES**: Tarjetas operacionales compactas con botones de investigación inmediata.
  - 🔍 **INVESTIGACIONES**: Registro cronológico de auditoría por caso.
  - 📁 **EVIDENCIA**: Bóveda de paquetes locales con verificación de integridad SHA-256.
  - 🗺️ **MAPA / ZONAS**: Vista de cobertura funcional y lógica de la tienda.
  - ⚙️ **ESTADO DEL SISTEMA**: Diagnóstico técnico de CPU, RAM, Disco y telemetría de flujos RTSP.

---

## 2. Requisitos del Sistema
- **Sistema Operativo**: Windows 10/11 (64-bit) o Linux x86_64.
- **Python**: 3.12+ (entorno virtual `.venv`).
- **Hardware Recomendado**: Intel Core i5/i7 (8va gen o superior) / AMD Ryzen 5/7, 8 GB RAM mínimo (16 GB recomendado para 15+ cámaras), almacenamiento SSD.

---

## 3. Inicio Rápido

Ejecutar la aplicación completa con:
```powershell
.\TukeVision.bat
```

O directamente mediante el launcher de Python:
```powershell
.\.venv\Scripts\python.exe scripts/launcher.py
```

---

## 4. Ejecución de Pruebas Automatizadas

```powershell
.\.venv\Scripts\pytest tests/ --basetemp=.pytest_tmp -q
```

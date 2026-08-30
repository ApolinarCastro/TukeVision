# ESTADO ACTUAL DE TUKEVISION (CURRENT_STATE)
**Fase:** F12 — Productización, Hardening y Consolidación de Producción  
**ID de Ejecución:** `TV-F12-PRODUCTION-PRODUCTIZATION-01`  
**Fecha:** 2026-08-30  
**Arquitectura:** Local-First · Edge Native · Cero Datos Fabricados  

---

## 1. Resumen Ejecutivo

TukeVision es una plataforma de software para centros de comando de videovigilancia e inteligencia retail y prevención de pérdidas en tiempo real. Opera bajo una arquitectura estricta **local-first** en hardware estándar (CPU x86_64, Windows/Linux), sin requerir conexión constante a la nube ni servidores externos obligatorios.

El sistema procesa simultáneamente flujos multicámara continuos (RTSP/H.264/H.265/archivos locales), ejecuta inferencia visual en el borde (OpenVINO / PyTorch), mantiene seguimiento temporal de entidades, correlaciona eventos espaciales en zonas delimitadas, empaqueta evidencia forense inmutable con hashes criptográficos SHA-256, y ofrece una interfaz gráfica reactiva y profesional construida en Tkinter bajo un sistema de diseño unificado en español (`es-CL`).

---

## 2. Pilares de la Implementación

### 2.1 Cero Inteligencia Fabricada (Zero Fake Data)
Todo dato visible en el Command Center proviene de una fuente física comprobada o de un cálculo determinista:
- **Hecho (`FACT`):** Detección de persona, trayectoria de tracker, cruce de zona, timestamp de cuadro, hash SHA-256.
- **Inferencia (`INFERENCE`):** Nivel de riesgo, tiempo de permanencia respecto a umbral, clasificación de evento.
- **Desconocido (`UNKNOWN`):** Marcado explícitamente cuando no hay datos suficientes. Nunca se inventan confianzas por defecto (e.g. 0.88/0.90) ni zonas o IDs ficticios.

### 2.2 Sistema de Diseño Unificado (`DesignTokens`)
- Paleta oscura slate/navy para centros de monitoreo 24/7 (`#0B0F19`, `#111827`, `#1F2937`).
- Estados semánticos unificados (`NORMAL`, `INFO`, `ATTENTION`, `CRITICAL`, `DEGRADED`, `OFFLINE`).
- Tipografías escaladas para monitores de alta y mediana resolución (1080p, 1440p, 4K).

### 2.3 Localización Nativa (`es-CL`)
- Vistas principales: `RESUMEN`, `EN VIVO`, `SITUACIONES`, `INVESTIGACIONES`, `EVIDENCIA`, `MAPA / ZONAS`, `ESTADO DEL SISTEMA`.
- Botones de acción: `Detener`, `Ajustes`, `Revisión`, `Pantalla Completa`, `Zoom +`, `Zoom -`, `Restablecer`, `Volver a Cuadrícula`.
- HUD de Focus HD: `FUENTE: {res} | PRESENTACIÓN: {cw}x{ch} | INFERENCIA: 640x360 | PERFIL: PRINCIPAL (HD)`.

### 2.4 Preparación para Firma de Medios ONVIF (Media Signing)
- Modelo de evidencia compatible con estados de origen: `SOURCE_UNSIGNED` (predeterminado para cámaras RTSP locales estándar), `SIGNED_UNVERIFIED`, `SIGNED_VALID`, `SIGNATURE_INVALID`.
- Integridad local garantizada mediante sidecars `.json` y hashes SHA-256 inmutables por cada clip o imagen forense.

### 2.5 Liveness y Observabilidad
- Separación de `CAPTURE_HEALTH`, `PROCESSING_HEALTH` y `PRESENTATION_HEALTH`.
- Detección de cuadros congelados (`stale frame detection`) para evitar falsos estados de "en vivo" si el video se detiene.
- Telemetría en tiempo real: CPU, RAM, Disco, FPS Global y FPS por cámara con índices de generación y secuencia.

---

## 3. Estado de la Suite de Pruebas
- Más de 900 pruebas unitarias y de integración automatizadas.
- 0 fallos, 0 errores, 100% de regresión limpia.

# CAPACIDADES DEL PRODUCTO TUKEVISION (PRODUCT_CAPABILITIES)

**Documentación Canónica Viva**  
**ID:** `TV-F12-PRODUCTION-PRODUCTIZATION-01`  

---

## 1. Capacidades Operacionales Certificadas

| Capacidad | Estado | Descripción |
| :--- | :--- | :--- |
| **Monitoreo Multicámara Local** | **PRODUCCIÓN** | Visualización en vivo de hasta 16 cámaras simultáneas en cuadrículas simétricas (1, 4, 6, 9, 16) con reconexión automática y detección de pérdidas de señal. |
| **Foco HD con Zoom Digital** | **PRODUCCIÓN** | Doble clic o clic en cuadrícula para ampliar cualquier cámara a resolución completa (1080p nativa) manteniendo HUD técnico y zoom digital centrado en cursor (1x a 4x). |
| **Detección e Inferencia Edge** | **PRODUCCIÓN** | Inferencia continua optimizada con OpenVINO / CPU en cuadro escalado (640x360), garantizando alta tasa de cuadros sin saturar el sistema. |
| **Rastreo y Análisis de Permanencia** | **PRODUCCIÓN** | Seguimiento visual de personas mediante ByteTrack y cómputo de permanencia en zonas comerciales configurables. |
| **Empaquetado de Evidencia SHA-256** | **PRODUCCIÓN** | Generación automática de paquetes de evidencia forense (video MP4 + cuadro clave JPG + sidecar JSON) con firma criptográfica de integridad SHA-256. |
| **Búsqueda Semántica Bajo Demanda** | **PRODUCCIÓN** | Búsqueda acotada por tienda, cámara, intervalo temporal y entidad sobre índice SQLite local sin indexar 24/7 de forma masiva el almacenamiento. |
| **Preparación para Firma ONVIF** | **PRODUCCIÓN** | Trazabilidad del origen del flujo de video (`SOURCE_UNSIGNED` para cámaras convencionales, con soporte para certificados de firma). |
| **Interfaz en Español (`es-CL`)** | **PRODUCCIÓN** | Navegación operacional, botones, controles, alertas y métricas completamente traducidos a español chileno/latinoamericano. |

---

## 2. Límites y Fronteras Operacionales

1. **Grabación Continua:** La grabación de video 24/7 a largo plazo reside en el NVR/DVR local de la tienda. TukeVision preserva clips atómicos de eventos e investigaciones relevantes.
2. **Nivel de Autonomía:** El sistema opera bajo **AUTONOMÍA 2 (Gobernada)**. Las acciones sugeridas o alertas generadas son presentadas al operador humano para su validación o despacho.
3. **Hardware Recomendado:** Procesador Intel Core i5/i7 (8va gen+) o AMD Ryzen 5/7, 8 GB RAM mínimo (16 GB recomendado para 15+ cámaras), almacenamiento SSD.

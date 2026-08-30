# SISTEMA DE DISEÑO Y EXPERIENCIA DE USUARIO (UI_UX_SYSTEM)

**TukeVision Command Center V2**  
**ID:** `TV-F12-PRODUCTION-PRODUCTIZATION-01`  

---

## 1. Fundamentos de Diseño

La interfaz de usuario está optimizada para operadores de centros de control, salas de seguridad y monitoreo retail continuo. Su diseño prioriza la reducción de fatiga visual, el contraste inmediato de incidentes críticos y la claridad epistémica.

---

## 2. Tokens de Color (`DesignTokens.COLORS`)

| Token | Valor Hex | Uso Principal |
| :--- | :--- | :--- |
| `bg` | `#0B0F19` | Fondo principal del lienzo |
| `surface` | `#111827` | Superficie de paneles y tarjetas |
| `surface_elevated` | `#1F2937` | Encabezados de paneles y tarjetas destacadas |
| `border` | `#374151` | Bordes divisorios estándar |
| `border_light` | `#4B5563` | Bordes interactivos / hover |
| `text` | `#F9FAFB` | Texto principal de alto contraste |
| `text_secondary` | `#D1D5DB` | Texto secundario y descriptivo |
| `text_dim` | `#9CA3AF` | Metadatos y etiquetas secundarias |
| `accent` | `#00E5FF` | Elementos activos e interactivos |
| `normal` | `#10B981` | Estado saludable / Online / Nominal |
| `attention` | `#F59E0B` | Atención requerida / Estado degradado |
| `critical` | `#EF4444` | Alerta crítica / Flujo desconectado |

---

## 3. Jerarquía Tipográfica (`DesignTokens.FONTS`)

- **Título Principal (`title`):** Segoe UI 14pt Negrita (Encabezado de aplicación y vistas)
- **Título de Panel (`panel_title`):** Segoe UI 11pt Negrita (Títulos de tarjetas y secciones)
- **Cuerpo (`body`):** Segoe UI 9pt Regular (Lectura general de eventos)
- **Cuerpo Destacado (`body_bold`):** Segoe UI 9pt Negrita (Nombres de cámaras, acciones)
- **Texto Pequeño (`small`):** Segoe UI 8pt Regular (HUD, timestamps, metadatos)
- **Valor KPI (`kpi_value`):** Segoe UI 18pt Negrita (Números grandes en resumen)

---

## 4. Clasificación Epistémica Visual

Cada evento en las vistas operacionales se desglosa claramente en:
1. **HECHO (`FACT` - Verde `#10B981`):** Observación física comprobada (e.g. persona en cámara X, cruce de línea).
2. **INFERENCIA (`INFERENCE` - Azul/Índigo `#6366F1`):** Deducción por regla de negocio o modelo de IA (e.g. posible merodeo).
3. **DESCONOCIDO (`UNKNOWN` - Gris `#9CA3AF`):** Elementos que la IA no puede afirmar (e.g. intención del sujeto).

---

## 5. Accesos Rápidos y Teclado

- `Doble Clic` en cámara: Ingresar a Foco HD.
- `Doble Clic` en Foco HD: Alternar zoom digital (1x / 2x).
- `Rueda del Ratón`: Zoom digital continuo sobre el cursor (1x a 4x).
- `Arrastrar Ratón`: Desplazamiento panorámico (pan) cuando hay zoom activo.
- `Escape`: Salir de Foco HD o de Pantalla Completa y volver a la cuadrícula.

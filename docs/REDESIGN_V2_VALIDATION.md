# Auditoría y entrega del rediseño v2

Fecha: 16 de octubre de 2026, America/Lima.

**Estado: utilizable dentro del alcance revisado, con límites científicos explícitos.** Se implementaron los cambios en el repositorio real. La revisión es parcial respecto de la reconciliación completa con la fuente primaria, el zoom real al 200 % y una sesión de lector de pantalla. No se publicó ni desplegó la aplicación.

## Resultado y alcance

Las ocho funciones originales permanecen accesibles mediante navegación nativa: Fight brief, Fighter evidence, Tactical model, Outcome analysis, Sensitivity, Validation, Research report y Methodology. El combate, el corte temporal y la siguiente acción encabezan el flujo. Los perfiles comparten filas y unidades; las alternativas tienen asignaciones explícitas; la conclusión distingue utilidad calculada, incertidumbre y soporte empírico.

Se conservaron el snapshot `greco-5e38ebeb9bb8`, sus exclusiones, el modelo numérico persistido, las ecuaciones, las políticas, los pesos, las distribuciones y los umbrales científicos. El rediseño no reentrenó el modelo para mejorar su aspecto o conclusión. Un corte diferente requiere la acción explícita Prepare historical baseline. Abrir vistas y cambiar opciones visuales no ejecuta Monte Carlo.

El ejemplo anterior se reproduce con el mismo contexto, configuración, semilla y 5.000 iteraciones. La probabilidad base sigue siendo **0.6858367292839322**. La regresión compara árbol, medias, intervalos, diferencias pareadas, convergencia y sensibilidad con tolerancia absoluta `1e-12`. La auditoría independiente verificó las 8.420 filas históricas y sus diez predictores; el error máximo de acumulación fue `1.71e-13`, con el mismo patrón de valores ausentes. También reprodujo los valores de las 15.000 utilidades integradas y los puntos de sensibilidad del ejemplo.

El baseline **sigue siendo exploratorio**: 527 combates de prueba, Brier `0.2425234915`, log loss `0.6780815900`, accuracy `57.12 %`; el intervalo del 95 % para Brier(modelo) − Brier(0.5), `[-0.0161991, +0.0007692]`, incluye cero. Una auditoría de funcionamiento no demuestra calibración perfecta ni efectos tácticos causales.

## Cobertura de calidad del producto

Los denominadores siguientes son elementos del inventario revisado, no porcentajes de precisión ni garantías de comprobación exhaustiva. `0 / N` significa que no quedan defectos demostrados abiertos en esos elementos; los límites se conservan expresamente. El [registro de cobertura](../reports/audit_v2/coverage.json) y su [resumen generado](../reports/audit_v2/scorecard.md) contienen el detalle y las evidencias.

| Categoría | Defectos observados | Evaluación |
|---|---|---|
| Utilidad y completitud | 0 / 13 | Ocho funciones, controles de edición, cálculo, sensibilidad y cuatro exportaciones accesibles. Se ejercitó la carga nativa de cuatro CSV sintéticos, su aplicación y la restauración del snapshot original. |
| Claridad analítica | 0 / 19 | Contexto común y lenguaje de datos observados, estimaciones, supuestos y cálculos; unidades y procedencia junto a los resultados. |
| Consistencia visual e interacción | 0 / 21 | Ocho vistas revisadas; cuatro representativas en cinco resoluciones. Contraste y foco medidos. Permanecen sin verificar una sesión de lector de pantalla y zoom real al 200 %. |

## Corrección y robustez analítica

| Categoría | Defectos observados | Evaluación |
|---|---|---|
| Autoridad y confianza de fuentes | 0 / 13 | Hashes y archivo comunitario comprobados; la reconciliación completa contra UFCStats y los derechos de reutilización de la fuente original siguen pendientes. Los efectos tácticos se presentan como supuestos. |
| Exactitud de valores | 0 / 14 | Reproducción independiente y regresión contra el registro anterior, sin modificar los datos ni el modelo. |
| Acuerdo dentro de gráficos | 0 / 9 | Medias, bandas, ramas, ejes, símbolos, leyendas y puntos actuales corresponden al motor. Se corrigió la resolución porcentual de ejes con diferencias diminutas. |
| Detalles de fuentes | 0 / 12 | Combates contribuyentes, denominadores, particiones, parámetros, exclusiones y metadatos inspeccionables; alcance personalizado de sensibilidad separado del informe por defecto. |
| Consistencia entre registros | 0 / 13 | Identidad de configuración y copia inmutable de exportación; fecha de creación, snapshot, versión, semilla e iteraciones coherentes. |
| Controles de calidad de datos | 0 / 8 | Exclusiones temporales, identidades, formatos, resultados, datos ausentes y 0/0 comprobados. La verdad completa de la fuente primaria excede esta revisión. |
| Soporte de conclusiones | 0 / 11 | Empates y ausencia de preferencia robusta preservados; una región coloreada o una media mayor no se presentan como causalidad o recomendación robusta. |

## Hallazgos priorizados y reparaciones verificadas

1. **Interpretación de empates y baselines asumidos — Outcome analysis y HTML.** La prosa inicial podía asignar un líder arbitrario cuando las utilidades empataban, y el baseline manual recibía una etiqueta de bootstrap. **Corregido:** igualdad o máximo compartido explícitos; un único histograma cuando las distribuciones coinciden; baseline manual identificado como supuesto fijo sin intervalo empírico. Se mantuvieron los cálculos y el reparto de empates.

2. **Continuidad y vinculación de resultados — editores y navegación.** Era necesario separar borradores, valores aplicados y el registro calculado. **Corregido:** Apply/Cancel validan de forma atómica; el borrador persiste al navegar; una identidad incluye snapshot, modelo numérico, orden de peleadores, corte, división, rounds, fuente, parámetros, incertidumbre, semilla e iteraciones. Un cambio marca el registro previo como anterior; volver a una de las cuatro configuraciones recientes exactas recupera su resultado. Los errores conservan el último registro válido sin mostrarlo como ejecución vigente. Las rutas usan `screens/` para evitar el descubrimiento automático de páginas heredadas al abrir un enlace directo.

3. **Coherencia de exportación — Research report.** La creación de HTML podía producir fechas diferentes y el alcance de sensibilidad explorado no coincidía necesariamente con el exportado. **Corregido:** fecha fija del análisis, identidad, copia coherente HTML/CSV/JSON/ZIP y etiquetas de registro anterior. El informe conserva la cuadrícula de robustez declarada por el motor; las exploraciones personalizadas tienen sus propios CSV y un aviso explícito de alcance. Cambiar el snapshot elimina análisis y exportaciones anteriores; se observó pasar de cuatro descargas a ninguna tras importar una fuente sintética y restaurar después el archivo original.

4. **Lectura y accesibilidad visual — shell, combate y gráficos.** Se observaron nombres fragmentados en tableta, un control parcialmente oculto por la cabecera, texto secundario atenuado y ticks repetidos. **Corregido:** composición según el ancho real del combate, barra lateral compacta, espacio seguro bajo la cabecera, texto secundario opaco, paleta medida, símbolos/trazos/códigos además del color y ejes con resolución suficiente. Se repitieron las capturas afectadas. La carga inicial también conserva un estado de recuperación para recursos ausentes o inválidos.

## Verificación ejecutada

| Comprobación | Resultado y evidencia |
|---|---|
| Antes del rediseño | 48 pruebas aprobadas; Ruff correcto. [Registro inicial](../reports/audit_v2/tests_before.xml). No se ocultaron fallos preexistentes. |
| Suite completa | **68 pruebas aprobadas**, un aviso de deprecación de pandas/NumPy en el caso de historial vacío. [Registro final](../reports/audit_v2/tests_after.xml). Ruff check y format correctos. |
| Último ajuste de texto | Flujo completo existente repetido tras corregir la concordancia singular/plural y la serialización de la tabla técnica de parámetros. [Comprobación enfocada](../reports/audit_v2/final_copy_check.xml). |
| Estados y navegación | Ocho vistas, enlaces directos en arranque frío, Apply/Cancel, borrador al navegar, pesos y límites inválidos, cambio de semilla, resultado anterior, error de cálculo y recuperación exacta comprobados por AppTest. |
| Importación real del control | Cuatro CSV explícitamente sintéticos cargados mediante el selector nativo; validación, nuevo contexto, eliminación de descargas previas y restauración observados. [Evidencia](../reports/review_v2/import_checks.json). Los CSV originales no se editaron. |
| Revisión adaptable | Fight brief, Fighter evidence, Outcome analysis y Sensitivity a **1440×900, 1280×800, 1024×768, 768×1024 y 390×844**; restantes vistas a 1440×900. Sin scroll horizontal de página en esos recorridos. [Mediciones](../reports/review_v2/browser_checks.json). Las tablas extensas conservan su propio desplazamiento. |
| Contraste | Texto normal principal y secundario, navegación, acciones, avisos y códigos del mapa ≥4.5:1 en los pares medidos; borde de input 3.68:1 y foco 6.43:1. El gris del mapa se oscureció a `#6A737D` (4.82:1 con blanco). [Cálculos](../reports/review_v2/contrast.json). |
| Teclado | Navegación, aplicar supuestos, ejecutar, sensibilidad y generar informe con Enter; foco Tab de 3 px visible, con nombre y geometría inspeccionados. [Alcance](../reports/review_v2/accessibility_checks.json). No constituye certificación WCAG completa. |
| Ampliación | El navegador integrado no cambió su zoom mediante Ctrl++; **zoom real al 200 % sin verificar**. Se inspeccionó reflujo a 720 px como comprobación complementaria, sin contarlo como prueba de zoom. |
| Informe sin conexión e impresión | HTML con Plotly y fuentes incrustados, sin scripts, hojas de estilo o imágenes externas necesarios. Apertura local y renderizado desde archivo a A4 de diez páginas; gráficos y tablas inspeccionados, incluida escala de grises. PDF de revisión interno, sin añadir un nuevo contrato de exportación a la aplicación. |

## Límites y próximos controles concretos

- La evidencia empírica no permite declarar calibración perfecta ni una táctica causalmente óptima. Se conserva el soporte exploratorio y las limitaciones del bootstrap por combate, el archivo retrospectivo y la agregación entre divisiones y formatos.
- Falta reconciliar completamente los registros contra la fuente primaria y establecer sus derechos de reutilización. Los datos y artículos suministrados siguen fuera de Git.
- Faltan zoom real al 200 % y una sesión de lector de pantalla en un navegador que exponga esas capacidades. El control por teclado, el reflujo y los pares de contraste comprobados no sustituyen esas pruebas.
- El aviso de deprecación de pandas/NumPy es reproducible en la prueba de historial vacío; no produce fallo ni cambio numérico con las dependencias fijadas. Conviene revisarlo antes de una futura actualización de dependencias.

## Abrir y revisar

Desde PowerShell, en este repositorio: `./run.ps1`. La aplicación local usa [127.0.0.1:8501](http://127.0.0.1:8501/). El modelo por defecto existente se carga sin refit. El cálculo se inicia mediante Run analysis.

- [Galería antes/después y móvil](../reports/review_v2/index.html)
- [Brief visual, wireframes, navegación y contrato de estados](REDESIGN_V2.md)
- [Reproducción numérica independiente](../reports/audit_v2/numbers.json)
- [Informe autocontenido del ejemplo histórico](../reports/review_v2/report.html)
- [CSV de revisión](../reports/review_v2/policy_results.csv), [JSON](../reports/review_v2/analysis.json) y [ZIP](../reports/review_v2/research_bundle.zip)

No se añadieron dependencias Python o JavaScript de frontend. Se incluyeron tres archivos de IBM Plex con su licencia OFL y un script de adquisición reproducible. Las fuentes, la marca SVG y los recursos del informe son locales; la operación habitual no depende de Internet.

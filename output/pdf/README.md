# Guía visual de MMA Decision Lab

El PDF en esta carpeta contiene 20 páginas en español con capturas reales de la
interfaz v2, pasos de operación, interpretación de resultados, un ejemplo reproducible,
glosario y guion de presentación. Los gráficos se calculan con el motor existente.

## Procedencia

- Ejemplo: Khabib Nurmagomedov vs Conor McGregor, antes de 2018-10-06, Lightweight,
  5 rounds, snapshot `greco-5e38ebeb9bb8`.
- Escenario neutral y preset hipotético **de la interfaz**: s=.35, g=.50, R=.50,
  c=.10, semiancho=.15, concentración=30 y pesos .25/.50/.25.
- 5000 draws, semilla 422. El preset de otros ejemplos científicos puede diferir.
- `assets/guide_example.json` conserva las cifras sin redondear y la procedencia.
- `assets/screens/` contiene capturas originales, recortadas solo en el espacio
  del PDF. `assets/*.png` y `assets/*.svg` son gráficos a partir del registro.
- Fuentes IBM Plex distribuidas según la licencia incluida en `assets/fonts/`.

## Reconstrucción

1. Ejecutar `docs/guides/prepare_guide_example.py` con el entorno Python del proyecto.
   Carga el modelo guardado; no vuelve a entrenarlo.
2. Ejecutar `docs/guides/guide_figures.py` con el runtime de documentos (matplotlib,
   fontTools y brotli se mantienen aislados en `tmp/guide_libs`).
3. Ejecutar `docs/guides/build_usage_guide.py` con el runtime de documentos
   (ReportLab, Pillow).
4. Renderizar las 20 páginas con Poppler y revisar las imágenes en
   `tmp/pdfs/usage_guide/`. Ejecutar `docs/guides/verify_usage_guide.py` con el
   runtime de documentos (pdfplumber, pypdf).

Los scripts no modifican el código aplicativo, el modelo ni el conjunto científico.
La guía separa estimaciones empíricas, supuestos tácticos e integración numérica.

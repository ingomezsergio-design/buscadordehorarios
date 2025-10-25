# Planificador Oct/Nov — Sup, Score y Contrato + Responsive

Este ZIP incluye una versión **estática (HTML+CSS+JS sin servidor)** que:
- Muestra **Sup, Score y Contrato**.
- Carga **Octubre** (gid 1756623178) y **Noviembre** (gid 530216982) del mismo Spreadsheet:
  `18LDSIcvRwNHW8-Ja38q8Ll02o6DKxzhK8qrjwnR7R3Y`.
- **No imprime texto** dentro de los días cuando son estados especiales (Franco, Vacaciones, LSG, Feriado, etc.).
- Mejora el **responsive móvil** (oculta horarios con pantallas ultra chicas y mantiene solo el color por estado).
- No usa librerías externas (ideal para **Google Sites** o hosting simple).

## Cómo usar
1) Publicá tus hojas de **Octubre** y **Noviembre** como CSV (“Archivo > Publicar en la web > Hoja > CSV”).  
2) Verificá/ajustá los **nombres de columnas** en `index.html` sección `COLS`:
   - `Agente`, `Sup`, `Score`, `Contrato` + columnas de días: `"1"`, `"2"`, ..., `"31"`.
3) Abrí `index.html` en el navegador o subilo a Sites.
4) Elegí **Agente** y **Mes** y tocá **Buscar**.

## Integración con tu Flask existente
Si ya tenés un backend, podés **reemplazar sólo el HTML/CSS**:
- Copiá `static/styles.css` y usalo en tu template.
- Dentro de tu JS, asegurate de setear:
  ```js
  document.getElementById('sup').textContent = data.sup || '—';
  document.getElementById('score').textContent = data.score || '—';
  document.getElementById('contrato').textContent = data.contrato || '—';
  ```
- Para remover textos dentro del calendario, no pintes innerText cuando el estado sea especial.

## Notas
- El año está fijado en **2025** (ajustalo fácil en `renderCalendar` si fuera necesario).
- Si tus encabezados diferencian mayúsculas/minúsculas o tienen espacios, actualizá `COLS`.

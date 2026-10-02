---

# Plantillas base para correos

Las plantillas definen la estructura y el formato de los correos enviados automáticamente desde los playbooks.
Su objetivo es mantener un estilo visual uniforme y facilitar la personalización de cada reporte.

---

## Estructura de los correos

Cada correo sigue una estructura básica compuesta por un **encabezado**, un **contenido principal**, y un **pie de página**:

```html
<!DOCTYPE html>
<html>
<head></head>
<body>
  <table>
    Header (header.html)
      <tr>
        <td>Contenido principal (informativo / tablas)</td>
      </tr>
    Footer (footer.html)
  </table>
</body>
</html>
```

---

### Automáticas

Las plantillas de **header** y **footer** se incluyen automáticamente para mantener un formato estándar en todos los correos.
Estas contienen elementos comunes como logotipos, colores corporativos y pie de firma.

Archivos utilizados:

* `header.html`
* `footer.html`

---

### Plantillas iniciales para copiar y modificar

Se incluyen plantillas base que pueden copiarse y adaptarse según el tipo de reporte que se necesite generar.

* `base_tabla.j2` → Recomendado para reportes con datos tabulares.
* `base_info.j2` → Ideal para mensajes informativos o resúmenes simples.

El objetivo es agilizar la creación de nuevos correos sin perder consistencia en el formato.

---

### Estilos generales

Parámetros principales usados en los correos:

* **Color institucional (banners):** `#da291c`
* **Fuente:** `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif`
* **Tamaño recomendado para el contenido principal:** entre `80%` y `100%` del ancho total

Estos valores garantizan una presentación clara, legible y acorde al diseño corporativo.

---

### Ejemplo de uso en playbook

```yaml
vars:
  titulo_reporte: "TITULO"
  actividad: "{{ SUBTITULO | default('') }}"
  signature_b64: "{{ lookup('file', playbook_dir ~ '/../resources/img/FirmaClaro.gif') | b64encode }}"
  header_template: "{{ playbook_dir }}/../resources/templates/mail/header.html"
  footer_template: "{{ playbook_dir }}/../resources/templates/mail/footer.html"
```

En este ejemplo se definen las variables para el título, subtítulo y firma del correo, además de las rutas a las plantillas de encabezado y pie de página que serán incluidas automáticamente.

---

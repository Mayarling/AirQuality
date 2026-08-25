/*
 * Arma la presentacion de la defensa.
 *
 * Se ejecuta desde la raiz del repositorio:
 *
 *     node presentacion/armar_presentacion.js
 *
 * Deja el archivo en presentacion/grupo8_mlops.pptx
 *
 * Los colores son los mismos de las figuras del proyecto, para que la
 * presentacion y el informe se vean como un solo trabajo.
 */

const pptxgen = require("pptxgenjs");
const path = require("path");

const RAIZ = path.resolve(__dirname, "..");
const FIG = (n) => path.join(RAIZ, "reports", "figuras", n);

// --- Paleta ---------------------------------------------------------------
const TINTA = "0E1A2B";        // fondo de las laminas oscuras
const TINTA_2 = "16273D";      // tarjetas sobre fondo oscuro
const AZUL = "2A78D6";
const AQUA = "1BAF7A";
const NARANJA = "EB6834";
const BLANCO = "FFFFFF";
const HUMO = "F4F6F9";         // fondo de tarjetas en laminas claras
const GRIS = "5C6570";         // texto secundario
const NEGRO = "12181F";

const TITULAR = "Cambria";
const CUERPO = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";   // 13.3 x 7.5
pres.author = "Grupo 8";
pres.title = "Pronostico de benceno a 24 horas";

const W = 13.3;
const H = 7.5;
const M = 0.62;                // margen

// --------------------------------------------------------------------------
// Piezas que se repiten
// --------------------------------------------------------------------------

/** El motivo del proyecto: el numero de la lamina dentro de un circulo. */
function chapa(slide, numero, color) {
  slide.addShape(pres.ShapeType.ellipse, {
    x: M, y: 0.42, w: 0.44, h: 0.44,
    fill: { color: color || AZUL },
  });
  slide.addText(String(numero), {
    x: M, y: 0.42, w: 0.44, h: 0.44,
    align: "center", valign: "middle",
    fontFace: CUERPO, fontSize: 13, bold: true, color: BLANCO, margin: 0,
  });
}

function titulo(slide, texto, numero, opciones) {
  const o = opciones || {};
  chapa(slide, numero, o.chapa);
  slide.addText(texto, {
    x: M + 0.62, y: 0.36, w: W - M * 2 - 0.62, h: 0.58,
    fontFace: TITULAR, fontSize: 30, bold: true,
    color: o.claro ? BLANCO : NEGRO, margin: 0, valign: "middle",
  });
}

function bajada(slide, texto, opciones) {
  const o = opciones || {};
  slide.addText(texto, {
    x: M + 0.62, y: 1.0, w: W - M * 2 - 0.62, h: 0.42,
    fontFace: CUERPO, fontSize: 14,
    color: o.claro ? "AFC0D4" : GRIS, margin: 0, valign: "middle",
  });
}

/** Tarjeta con fondo suave. Devuelve nada, solo dibuja. */
function tarjeta(slide, x, y, w, h, oscura) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: oscura ? TINTA_2 : HUMO },
    line: { color: oscura ? TINTA_2 : "E3E8EF", width: 1 },
  });
}

/** Numero grande con su etiqueta debajo. */
function cifra(slide, x, y, w, valor, etiqueta, color, oscura) {
  slide.addText(valor, {
    x, y, w, h: 0.72,
    fontFace: TITULAR, fontSize: 38, bold: true, color: color,
    align: "center", valign: "middle", margin: 0,
  });
  slide.addText(etiqueta, {
    x, y: y + 0.72, w, h: 0.5,
    fontFace: CUERPO, fontSize: 11,
    color: oscura ? "AFC0D4" : GRIS,
    align: "center", valign: "top", margin: 0,
  });
}

/** Fila de icono redondo + encabezado + descripcion. */
function fila(slide, x, y, w, marca, encabezado, texto, color) {
  slide.addShape(pres.ShapeType.ellipse, {
    x, y: y + 0.04, w: 0.42, h: 0.42, fill: { color: color },
  });
  slide.addText(marca, {
    x, y: y + 0.04, w: 0.42, h: 0.42,
    align: "center", valign: "middle",
    fontFace: CUERPO, fontSize: 12, bold: true, color: BLANCO, margin: 0,
  });
  slide.addText(encabezado, {
    x: x + 0.58, y, w: w - 0.58, h: 0.32,
    fontFace: CUERPO, fontSize: 14, bold: true, color: NEGRO, margin: 0,
    valign: "middle",
  });
  slide.addText(texto, {
    x: x + 0.58, y: y + 0.32, w: w - 0.58, h: 0.72,
    fontFace: CUERPO, fontSize: 11.5, color: GRIS, margin: 0, valign: "top",
  });
}

function laminaOscura(slide) {
  slide.background = { color: TINTA };
}

// --------------------------------------------------------------------------
// 1 · Portada
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  laminaOscura(s);

  s.addShape(pres.ShapeType.ellipse, {
    x: M, y: 1.5, w: 0.5, h: 0.5, fill: { color: AQUA },
  });

  s.addText("Pronóstico de benceno\na 24 horas", {
    x: M, y: 2.15, w: 8.4, h: 2.0,
    fontFace: TITULAR, fontSize: 46, bold: true, color: BLANCO,
    lineSpacing: 52, margin: 0,
  });

  s.addText("Un sistema MLOps completo: de los datos crudos a un servicio vigilado", {
    x: M, y: 4.25, w: 8.4, h: 0.45,
    fontFace: CUERPO, fontSize: 16, color: "AFC0D4", margin: 0,
  });

  s.addShape(pres.ShapeType.rect, {
    x: M, y: 5.05, w: 2.2, h: 0.03, fill: { color: NARANJA },
  });

  s.addText("Grupo #8", {
    x: M, y: 5.35, w: 4.0, h: 0.35,
    fontFace: CUERPO, fontSize: 15, bold: true, color: NARANJA, margin: 0,
  });
  s.addText("Mayarling Martínez  ·  Nicole Chavarría", {
    x: M, y: 5.72, w: 6.0, h: 0.35,
    fontFace: CUERPO, fontSize: 14, color: BLANCO, margin: 0,
  });

  // Las tres cifras que resumen el trabajo
  const cx = 9.35;
  tarjeta(s, cx, 1.9, 3.35, 4.2, true);
  cifra(s, cx, 2.15, 3.35, "2.905", "MAE en µg/m³", AQUA, true);
  cifra(s, cx, 3.4, 3.35, "27.8%", "menos error que el baseline", AZUL, true);
  cifra(s, cx, 4.65, 3.35, "56", "pruebas automáticas", NARANJA, true);

  s.addNotes(
    "Mayarling abre. Nos presentamos y decimos que el proyecto es un pipeline " +
    "completo, no solo un modelo. Las tres cifras de la derecha son el resumen: " +
    "el error, cuanto le ganamos al modelo tonto y las pruebas que lo respaldan."
  );
}

// --------------------------------------------------------------------------
// 2 · El problema
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  titulo(s, "El problema", 1);
  bajada(s, "Pronosticar el benceno del aire con un día de anticipación");

  s.addText(
    [
      { text: "El benceno sale del tráfico y es cancerígeno. No hay un nivel seguro.", options: { bullet: true, breakLine: true } },
      { text: "Con 24 horas de aviso se puede restringir el tráfico, avisar a la población y proteger a la gente sensible.", options: { bullet: true, breakLine: true } },
      { text: "Con una hora de aviso no se organiza nada.", options: { bullet: true } },
    ],
    {
      x: M, y: 1.75, w: 6.5, h: 1.7,
      fontFace: CUERPO, fontSize: 14.5, color: NEGRO,
      paraSpaceAfter: 8, margin: 0, valign: "top",
    }
  );

  tarjeta(s, M, 3.65, 6.5, 2.35);
  s.addText("La restricción que gobierna todo el diseño", {
    x: M + 0.32, y: 3.9, w: 5.9, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: NARANJA, margin: 0,
  });
  s.addText(
    "A la hora de hoy no podemos usar ningún dato de las próximas 23 horas, " +
    "porque en la vida real todavía no habrían ocurrido.\n\n" +
    "Ese horizonte de 24 horas es lo que hace el problema difícil, y lo dejamos " +
    "así a propósito.",
    {
      x: M + 0.32, y: 4.3, w: 5.9, h: 2.0,
      fontFace: CUERPO, fontSize: 13, color: NEGRO, margin: 0, valign: "top",
    }
  );

  const dx = 7.55;
  tarjeta(s, dx, 1.75, 5.15, 4.8);
  s.addText("Cómo medimos", {
    x: dx + 0.32, y: 2.0, w: 4.5, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: AZUL, margin: 0,
  });
  s.addText(
    [
      { text: "MAE en µg/m³ ", options: { bold: true } },
      { text: "— \"en promedio nos equivocamos por tantos microgramos\"", options: {} },
    ],
    { x: dx + 0.32, y: 2.42, w: 4.5, h: 0.6, fontFace: CUERPO, fontSize: 13, color: NEGRO, margin: 0 }
  );

  s.addText("Por qué el MAPE no sirve acá", {
    x: dx + 0.32, y: 3.15, w: 4.5, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: NARANJA, margin: 0,
  });
  s.addText(
    "El lote 2 tiene el MAPE más alto (78.7%) y NO el peor MAE. Cuando el " +
    "benceno baja en invierno, un error chiquito se vuelve un porcentaje enorme.",
    { x: dx + 0.32, y: 3.57, w: 4.5, h: 1.0, fontFace: CUERPO, fontSize: 13, color: NEGRO, margin: 0, valign: "top" }
  );

  s.addText("Lo que nos pusimos como meta", {
    x: dx + 0.32, y: 4.72, w: 4.5, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: AQUA, margin: 0,
  });
  s.addText(
    [
      { text: "Ganarle al menos 10% al baseline", options: { bullet: true, breakLine: true } },
      { text: "No pasar de 5 µg/m³ de error", options: { bullet: true } },
    ],
    { x: dx + 0.32, y: 5.14, w: 4.5, h: 1.1, fontFace: CUERPO, fontSize: 13, color: NEGRO, margin: 0, paraSpaceAfter: 4 }
  );

  s.addNotes(
    "Mayarling. Lo importante de esta lamina es que las metas las fijamos ANTES " +
    "de entrenar, y que descartamos el MAPE con evidencia nuestra, no por gusto."
  );
}

// --------------------------------------------------------------------------
// 3 · Los datos
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  titulo(s, "Los datos, y lo que encontramos al leerlos", 2);
  bajada(s, "Air Quality de UCI · 9 357 horas seguidas · marzo 2004 a abril 2005");

  fila(s, M, 1.85, 7.0, "1",
    "El archivo está mal formado para lectura directa",
    "Separador punto y coma, coma como decimal, columnas y filas vacías. Leído " +
    "normal, todos los números entran como texto.", AZUL);

  fila(s, M, 3.05, 7.0, "2",
    "Los faltantes vienen escritos como −200",
    "No son celdas vacías. Sin convertirlos primero, los promedios salen " +
    "negativos y todo el análisis queda mal.", AZUL);

  fila(s, M, 4.25, 7.0, "3",
    "Los huecos no están sueltos: son apagones del equipo",
    "366 faltantes que en realidad son 16 periodos continuos sin medir. El más " +
    "largo dura 76 horas. Esto cambió cómo limpiamos.", NARANJA);

  tarjeta(s, M, 5.6, 7.0, 1.0);
  s.addText(
    "Por eso interpolamos solo los huecos que caben enteros en 3 horas. " +
    "Rellenar tres días seguidos sería inventar datos.",
    { x: M + 0.3, y: 5.72, w: 6.4, h: 0.8, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, valign: "middle", italic: true }
  );

  const dx = 8.05;
  tarjeta(s, dx, 1.85, 4.65, 4.75);
  cifra(s, dx, 2.05, 4.65, "9 357", "horas en el archivo original", AZUL);
  cifra(s, dx, 3.25, 4.65, "16", "apagones del equipo, el mayor de 76 horas", NARANJA);
  cifra(s, dx, 4.55, 4.65, "90.23%", "de NMHC(GT) son faltantes: se descarta la columna", GRIS);

  s.addNotes(
    "Nicole. El punto fuerte es el tercero: pasar de \"hay 366 nulos\" a \"son 16 " +
    "apagones\" es lo que separa mirar una tabla de entender los datos. Si alguien " +
    "pregunta, la pagina de UCI dice que el periodo termina en febrero pero el " +
    "archivo llega hasta abril: nos guiamos por el archivo."
  );
}

// --------------------------------------------------------------------------
// 4 · Arquitectura
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  titulo(s, "Arquitectura", 3);
  bajada(s, "Cada caja lleva debajo el archivo del repositorio que la implementa");

  // Se usa la version sin titulo de la imagen: la lamina ya lleva el suyo.
  s.addImage({ path: FIG("12_arquitectura_lamina.png"), x: 0.72, y: 1.5, w: 11.9, h: 5.45 });

  s.addNotes(
    "Mayarling. Recorrer el camino de izquierda a derecha y de arriba abajo. " +
    "Senalar las dos flechas naranjas punteadas: la que corta el pipeline si falla " +
    "una regla dura, y la que vuelve al entrenamiento si la decision dice " +
    "REENTRENAR. Y decir que la simulacion de danos usa LAS MISMAS reglas."
  );
}

// --------------------------------------------------------------------------
// 5 · Calidad de los datos
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  titulo(s, "Data Quality Gates", 4);
  bajada(s, "Nueve reglas que corren dos veces: a la entrada y a la salida de la limpieza");

  tarjeta(s, M, 1.85, 6.0, 4.6);
  s.addText("Reglas duras — detienen el pipeline", {
    x: M + 0.32, y: 2.05, w: 5.4, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: NARANJA, margin: 0,
  });
  s.addText(
    [
      { text: "R01  el esquema de columnas es el esperado", options: { breakLine: true } },
      { text: "R02  llega la cantidad mínima de filas", options: { breakLine: true } },
      { text: "R03  no hay marcas de tiempo repetidas", options: { breakLine: true } },
      { text: "R05  los valores están en rangos físicos posibles", options: { breakLine: true } },
      { text: "R07  no hay más de 1% de filas duplicadas", options: { breakLine: true } },
      { text: "R09  los tipos de dato son numéricos donde deben", options: {} },
    ],
    { x: M + 0.32, y: 2.5, w: 5.4, h: 2.0, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, lineSpacing: 21 }
  );

  s.addText("Reglas blandas — avisan y siguen", {
    x: M + 0.32, y: 4.6, w: 5.4, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: AZUL, margin: 0,
  });
  s.addText(
    [
      { text: "R04  la serie horaria es continua", options: { breakLine: true } },
      { text: "R06  el target no pasa de 10% de huecos", options: { breakLine: true } },
      { text: "R08  ninguna columna es constante", options: {} },
    ],
    { x: M + 0.32, y: 5.05, w: 5.4, h: 1.1, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, lineSpacing: 21 }
  );

  const dx = 7.1;
  tarjeta(s, dx, 1.85, 5.6, 4.6);
  s.addText("Por qué la diferencia importa", {
    x: dx + 0.32, y: 2.05, w: 5.0, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: AQUA, margin: 0,
  });
  s.addText(
    "Que falten unas horas sueltas es normal en un equipo real y no justifica " +
    "botar toda la corrida.\n\n" +
    "Que aparezca una columna que no existía, sí: a partir de ahí nada de lo que " +
    "se calcule significa lo mismo.\n\n" +
    "Si todas las reglas detuvieran el pipeline, la gente terminaría " +
    "desactivándolas. Y unas reglas apagadas no sirven de nada.",
    { x: dx + 0.32, y: 2.5, w: 5.0, h: 2.5, fontFace: CUERPO, fontSize: 13, color: NEGRO, margin: 0, valign: "top" }
  );

  s.addText("Corren dos veces, y no es repetición", {
    x: dx + 0.32, y: 4.95, w: 5.0, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: NARANJA, margin: 0,
  });
  s.addText(
    "A la entrada, sobre los datos crudos. Y a la salida, sobre los ya limpios. " +
    "La segunda pasada es la que comprueba que la limpieza no rompió nada.",
    { x: dx + 0.32, y: 5.38, w: 5.0, h: 1.0, fontFace: CUERPO, fontSize: 13, color: NEGRO, margin: 0, valign: "top" }
  );

  s.addNotes(
    "Nicole. Insistir en la separacion dura/blanda: es una decision de diseno, no " +
    "un descuido. Y en que las reglas corren dos veces, porque la segunda pasada " +
    "es la que comprueba que la limpieza no rompio nada."
  );
}

// --------------------------------------------------------------------------
// 6 · Sin leakage
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  laminaOscura(s);
  titulo(s, "La decisión de la que estamos más conformes", 5, { claro: true, chapa: NARANJA });
  bajada(s, "El anti-leakage no está en un comentario: está programado", { claro: true });

  s.addText(
    "Todos los rezagos se miden desde la hora que se quiere predecir, no desde ahora.\n\n" +
    "Para predecir t+24, el dato más reciente que existe es el de la hora t, que " +
    "respecto de t+24 es un rezago de 24 horas.\n\n" +
    "Un rezago de 1 hora usaría el dato de t+23, que todavía no ocurrió.",
    { x: M, y: 1.85, w: 5.9, h: 2.6, fontFace: CUERPO, fontSize: 14, color: BLANCO, margin: 0, valign: "top" }
  );

  s.addText(
    "Los comentarios no detienen a nadie. Por eso el proceso se cae solo si " +
    "alguien pide un rezago menor que el horizonte.",
    { x: M, y: 4.35, w: 5.9, h: 0.9, fontFace: CUERPO, fontSize: 13.5, color: NARANJA, margin: 0, valign: "top", italic: true }
  );

  tarjeta(s, 6.95, 1.85, 5.75, 2.95, true);
  s.addText(
    "def _validar_rezago(rezago, horizonte):\n" +
    "    if rezago < horizonte:\n" +
    "        raise ErrorDeLeakage(\n" +
    "            f\"Se pidio un rezago de \"\n" +
    "            f\"{rezago} h con un horizonte \"\n" +
    "            f\"de {horizonte} h. ...\")",
    {
      x: 7.25, y: 2.1, w: 5.2, h: 3.0,
      fontFace: "Courier New", fontSize: 12.5, color: "9EE8C8", margin: 0, valign: "top",
      lineSpacing: 20,
    }
  );

  s.addText(
    "Excepción deliberada: las variables de calendario sí se calculan sobre la " +
    "hora que se quiere predecir. Qué día va a ser mañana se sabe hoy.",
    { x: 6.95, y: 5.0, w: 5.75, h: 0.9, fontFace: CUERPO, fontSize: 12.5, color: "AFC0D4", margin: 0, valign: "top" }
  );

  tarjeta(s, M, 5.5, 12.06, 1.35, true);
  s.addText(
    "El caso extremo: PT08.S2(NMHC) correlaciona 0.982 con el benceno. Usarlo sin rezagar " +
    "daría métricas espectaculares y un modelo inútil, porque esa lectura no existe hasta " +
    "que llega la hora. Una métrica muy buena puede ser una señal de alarma.",
    { x: M + 0.32, y: 5.5, w: 11.4, h: 1.35, fontFace: CUERPO, fontSize: 13, color: BLANCO, margin: 0, valign: "middle" }
  );

  s.addNotes(
    "Mayarling. Esta es la lamina que hay que defender mejor. Contar tambien el " +
    "caso de PT08.S2, que correlaciona 0.982 con el benceno: usarlo sin rezagar " +
    "daria metricas espectaculares y un modelo inutil. Por eso una metrica muy " +
    "buena puede ser una senal de alarma."
  );
}

// --------------------------------------------------------------------------
// 7 · Modelado
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  titulo(s, "Cuatro modelos, y cómo se escogió", 6);
  bajada(s, "No gana el mejor: gana el que cumple los tres criterios fijados de antemano");

  s.addChart(
    pres.ChartType.bar,
    [{
      name: "MAE en validación",
      labels: ["baseline", "ridge", "random_forest", "gradient_boosting"],
      values: [4.021, 3.096, 3.043, 2.905],
    }],
    {
      x: M, y: 1.8, w: 6.4, h: 3.5,
      barDir: "col",
      chartColors: [GRIS, AZUL, AZUL, AQUA],
      varyColors: true,
      showTitle: true,
      title: "MAE en validación (µg/m³) — más bajo es mejor",
      titleFontFace: CUERPO, titleFontSize: 12, titleColor: NEGRO,
      showValue: true, dataLabelPosition: "outEnd",
      dataLabelFontFace: CUERPO, dataLabelFontSize: 11, dataLabelColor: NEGRO,
      dataLabelFormatCode: "0.000",
      showLegend: false,
      catAxisLabelColor: GRIS, catAxisLabelFontFace: CUERPO, catAxisLabelFontSize: 10,
      valAxisLabelColor: GRIS, valAxisLabelFontFace: CUERPO, valAxisLabelFontSize: 10,
      valGridLine: { color: "E3E8EF", size: 1 },
      catGridLine: { style: "none" },
      valAxisMinVal: 0,
      valAxisMaxVal: 4.5,
      valAxisMajorUnit: 1,
    }
  );

  tarjeta(s, M, 5.5, 6.4, 1.15);
  s.addText(
    "El baseline es repetir el valor de ayer a la misma hora. Si un modelo " +
    "complicado apenas le empata, no compensa mantenerlo en producción.",
    { x: M + 0.3, y: 5.5, w: 5.8, h: 1.15, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, valign: "middle" }
  );

  const dx = 7.5;
  s.addText("Los tres criterios, fijados antes de ver resultados", {
    x: dx, y: 2.05, w: 5.2, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: AZUL, margin: 0,
  });
  s.addText(
    [
      { text: "Ganarle al baseline por al menos 10% de MAE", options: { bullet: true, breakLine: true } },
      { text: "Que validación no sea más de 60% peor que entrenamiento", options: { bullet: true, breakLine: true } },
      { text: "Que el MAE no pase de 5.0 µg/m³", options: { bullet: true } },
    ],
    { x: dx, y: 2.5, w: 5.2, h: 1.3, fontFace: CUERPO, fontSize: 13, color: NEGRO, margin: 0, paraSpaceAfter: 6, valign: "top" }
  );

  tarjeta(s, dx, 3.9, 5.2, 2.75);
  s.addText("El criterio funcionó solo", {
    x: dx + 0.3, y: 4.08, w: 4.6, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: NARANJA, margin: 0,
  });
  s.addText(
    "random_forest quedó RECHAZADO aunque su MAE era mejor que el de ridge: se " +
    "degradaba 68.4% de entrenamiento a validación. Se había aprendido el ruido.\n\n" +
    "Gana gradient_boosting con 2.905 µg/m³ y 27.8% menos error que el baseline.",
    { x: dx + 0.3, y: 4.52, w: 4.6, h: 2.0, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, valign: "top" }
  );

  s.addNotes(
    "Mayarling. El punto de venta es el rechazo de random_forest: demuestra que " +
    "los criterios no son decoracion. Si preguntan por ridge, decir que se degrada " +
    "solo 8.2% contra el 50.7% del ganador, y que con mas historico seria un " +
    "candidato serio."
  );
}

// --------------------------------------------------------------------------
// 8 · MLflow
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  titulo(s, "Trazabilidad con MLflow", 7);
  bajada(s, "Experimento air-quality-benceno-24h · modelo grupo8-benceno-24h");

  const anchoT = 2.79;
  const datos = [
    ["15", "parámetros por corrida", AZUL],
    ["42", "métricas por corrida", AZUL],
    ["5", "artefactos por corrida", AQUA],
    ["2", "versiones registradas", NARANJA],
  ];
  datos.forEach((d, i) => {
    const x = M + i * (anchoT + 0.3);   // 4 tarjetas de 2.79 con 0.3 de aire
    tarjeta(s, x, 1.85, anchoT, 1.75);
    cifra(s, x, 2.0, anchoT, d[0], d[1], d[2]);
  });

  tarjeta(s, M, 3.85, 5.88, 3.1);
  s.addText("El ciclo de vida, con alias y no con stages", {
    x: M + 0.32, y: 4.05, w: 5.3, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: AQUA, margin: 0,
  });
  s.addText("Experiment   →   candidato   →   produccion", {
    x: M + 0.32, y: 4.5, w: 5.4, h: 0.45,
    fontFace: "Courier New", fontSize: 14, bold: true, color: NEGRO, margin: 0,
  });
  s.addText(
    "El entrenamiento registra la versión, le pone el alias candidato, comprueba " +
    "los tres criterios y solo entonces mueve el alias produccion.\n\n" +
    "Usamos alias porque los stages quedaron obsoletos: lo avisa la propia " +
    "interfaz de MLflow.",
    { x: M + 0.32, y: 5.05, w: 5.4, h: 1.8, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, valign: "top" }
  );

  tarjeta(s, 6.8, 3.85, 5.88, 3.1);
  s.addText("Dos cosas que valen doble", {
    x: 7.12, y: 4.05, w: 5.24, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: NARANJA, margin: 0,
  });
  s.addText(
    "Guardamos el md5 del archivo como parámetro data_version. Con eso, de " +
    "cualquier modelo se sabe con qué datos exactos se entrenó.\n\n" +
    "Las dos versiones registradas tienen métricas idénticas hasta el último " +
    "decimal: misma semilla, mismos cortes, mismo resultado. Eso es " +
    "reproducibilidad demostrada, no prometida.",
    { x: 7.12, y: 4.5, w: 5.24, h: 2.4, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, valign: "top" }
  );

  s.addNotes(
    "Mayarling. Mostrar aqui la captura del Model Registry si hay tiempo. El " +
    "argumento del md5 es el que convierte \"el modelo del martes\" en una " +
    "referencia y no en una descripcion."
  );
}

// --------------------------------------------------------------------------
// 9 · API y Docker
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  titulo(s, "El servicio: API y contenedor", 8);
  bajada(s, "Seis endpoints en FastAPI, dentro de una imagen reproducible");

  tarjeta(s, M, 1.85, 6.0, 2.5);
  s.addText("La decisión importante de la API", {
    x: M + 0.32, y: 2.05, w: 5.4, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: AZUL, margin: 0,
  });
  s.addText(
    "La entrada no son las 18 variables ya calculadas, sino las últimas 145 horas " +
    "de mediciones. La API construye las variables por dentro llamando a la misma " +
    "función que usó el entrenamiento.\n\n" +
    "Si las armara por su cuenta, cualquier diferencia pasaría desapercibida. Ese " +
    "error tiene nombre: training-serving skew.",
    { x: M + 0.32, y: 2.5, w: 5.4, h: 1.8, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, valign: "top" }
  );

  tarjeta(s, M, 4.55, 6.0, 2.4);
  s.addText("Los seis endpoints", {
    x: M + 0.32, y: 4.72, w: 5.4, h: 0.32,
    fontFace: CUERPO, fontSize: 14, bold: true, color: AQUA, margin: 0,
  });
  s.addText(
    [
      { text: "GET  /              información del servicio", options: { breakLine: true } },
      { text: "GET  /health        si está vivo y si el modelo cargó", options: { breakLine: true } },
      { text: "GET  /model-info    qué modelo y qué versión sirve", options: { breakLine: true } },
      { text: "GET  /metrics       latencia, errores, disponibilidad", options: { breakLine: true } },
      { text: "POST /predict       un pronóstico", options: { breakLine: true } },
      { text: "POST /predict/batch varios de una vez", options: {} },
    ],
    { x: M + 0.32, y: 5.12, w: 5.4, h: 1.7, fontFace: "Courier New", fontSize: 10.5, color: NEGRO, margin: 0, lineSpacing: 16 }
  );

  const dx = 6.9;
  s.addText("Las cuatro decisiones de la imagen", {
    x: dx, y: 1.85, w: 5.8, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: NARANJA, margin: 0,
  });
  s.addText(
    [
      { text: "Versión fija python:3.12-slim, nunca latest, para que la imagen no cambie sola", options: { bullet: true, breakLine: true } },
      { text: "Los requisitos se copian antes que el código, para aprovechar la caché", options: { bullet: true, breakLine: true } },
      { text: "Solo se instala lo que la API necesita, sin MLflow ni matplotlib", options: { bullet: true, breakLine: true } },
      { text: "Corre con un usuario sin privilegios, no como root", options: { bullet: true } },
    ],
    { x: dx, y: 2.3, w: 5.8, h: 2.1, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, paraSpaceAfter: 6, valign: "top" }
  );

  tarjeta(s, dx, 4.55, 5.8, 2.4);
  s.addText("Lo medimos construyendo las dos imágenes", {
    x: dx + 0.32, y: 4.72, w: 5.2, h: 0.32,
    fontFace: CUERPO, fontSize: 13, bold: true, color: NEGRO, margin: 0,
  });
  cifra(s, dx + 0.2, 5.15, 2.6, "1.33 GB", "con todo instalado", GRIS);
  cifra(s, dx + 2.95, 5.15, 2.6, "865 MB", "solo lo que la API usa", AQUA);

  s.addNotes(
    "Nicole. Si preguntan por que hizo falta exportar el modelo aparte: MLflow " +
    "guarda rutas absolutas de Windows dentro de mlruns, y dentro del contenedor " +
    "esas rutas no existen. Al exportarlo, ademas, pudimos sacar MLflow de la " +
    "imagen entera."
  );
}

// --------------------------------------------------------------------------
// 10 · Monitoreo
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  titulo(s, "Monitoreo en tres dimensiones", 9);
  bajada(s, "Sistema, datos y modelo. Ninguno reemplaza a los otros");

  const cols = [
    ["System", "latencia, throughput, errores y disponibilidad", "GET /metrics\nlogs/pipeline.log", AZUL],
    ["Data", "que las distribuciones no cambien", "src/monitoring/\ndrift.py", AQUA],
    ["Model", "que el pronóstico siga acertando", "src/monitoring/\nmodel_metrics.py", NARANJA],
  ];
  cols.forEach((c, i) => {
    const x = M + i * 4.1;
    tarjeta(s, x, 1.85, 3.8, 2.5);
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.3, y: 2.1, w: 0.4, h: 0.4, fill: { color: c[3] } });
    s.addText(c[0], {
      x: x + 0.85, y: 2.1, w: 2.7, h: 0.4,
      fontFace: CUERPO, fontSize: 16, bold: true, color: NEGRO, margin: 0, valign: "middle",
    });
    s.addText(c[1], {
      x: x + 0.3, y: 2.65, w: 3.2, h: 0.85,
      fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, valign: "top",
    });
    s.addText(c[2], {
      x: x + 0.3, y: 3.55, w: 3.2, h: 0.6,
      fontFace: "Courier New", fontSize: 10, color: GRIS, margin: 0, valign: "top",
    });
  });

  s.addText("Cuatro medidas de drift, no una", {
    x: M, y: 4.6, w: 6.0, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: AZUL, margin: 0,
  });
  s.addText(
    [
      { text: "PSI — parte la variable en 10 tramos. Es la que usamos para decidir.", options: { bullet: true, breakLine: true } },
      { text: "Kolmogorov-Smirnov — la mayor distancia entre las curvas acumuladas.", options: { bullet: true, breakLine: true } },
      { text: "Wasserstein — cuánto habría que mover los datos.", options: { bullet: true, breakLine: true } },
      { text: "Jensen-Shannon — qué tan distintas son, de 0 a 1.", options: { bullet: true } },
    ],
    { x: M, y: 5.05, w: 6.0, h: 1.9, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, paraSpaceAfter: 5, valign: "top" }
  );

  tarjeta(s, 7.0, 4.6, 5.7, 2.35);
  s.addText("La comprobación de que el cálculo está bien", {
    x: 7.32, y: 4.78, w: 5.1, h: 0.34,
    fontFace: CUERPO, fontSize: 13.5, bold: true, color: AQUA, margin: 0,
  });
  s.addText(
    "Las variables de calendario dan PSI cercano a cero. Tiene que ser así: la " +
    "distribución de horas y días de la semana no cambia entre periodos.\n\n" +
    "Si dieran alto, el cálculo estaría mal. Los umbrales 0.10 y 0.25 vienen del " +
    "riesgo crediticio y no son leyes universales.",
    { x: 7.32, y: 5.2, w: 5.1, h: 1.7, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, valign: "top" }
  );

  s.addNotes(
    "Nicole. Cuidado con el p-valor de Kolmogorov-Smirnov: con miles de filas casi " +
    "cualquier diferencia sale significativa, por eso nunca decidimos con el solo."
  );
}

// --------------------------------------------------------------------------
// 11 · El hallazgo
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  laminaOscura(s);
  titulo(s, "Drift no es lo mismo que degradación", 10, { claro: true, chapa: NARANJA });
  bajada(s, "El hallazgo principal del monitoreo, medido con nuestros propios datos", { claro: true });

  // Dos graficos y no uno con dos ejes: las dos medidas tienen escalas que no
  // se pueden comparar, y juntarlas daria la impresion falsa de que una sigue
  // a la otra. Van como grafico nativo y no como imagen, para que los numeros
  // sean siempre los de la maquina donde se corrio el monitoreo.
  s.addChart(
    pres.ChartType.bar,
    [{ name: "PSI maximo", labels: ["batch1", "batch2", "batch3"],
       values: [1.671, 6.175, 3.265] }],
    {
      x: M, y: 1.75, w: 3.6, h: 2.85,
      barDir: "col", chartColors: [AZUL, AZUL, AZUL],
      showTitle: true, title: "Cuánto cambiaron los datos (PSI)",
      titleFontFace: CUERPO, titleFontSize: 11, titleColor: BLANCO,
      showValue: true, dataLabelPosition: "outEnd",
      dataLabelFontFace: CUERPO, dataLabelFontSize: 10, dataLabelColor: BLANCO,
      dataLabelFormatCode: "0.000",
      showLegend: false,
      catAxisLabelColor: "AFC0D4", catAxisLabelFontFace: CUERPO, catAxisLabelFontSize: 10,
      valAxisLabelColor: "AFC0D4", valAxisLabelFontFace: CUERPO, valAxisLabelFontSize: 10,
      valGridLine: { color: "24374F", size: 1 },
      catGridLine: { style: "none" },
      valAxisMinVal: 0, valAxisMaxVal: 7, valAxisMajorUnit: 2,
      plotArea: { fill: { color: TINTA } }, chartArea: { fill: { color: TINTA } },
    }
  );

  s.addChart(
    pres.ChartType.bar,
    [{ name: "Degradacion del MAE", labels: ["batch1", "batch2", "batch3"],
       values: [88.8, 51.1, -3.4] }],
    {
      x: M + 3.75, y: 1.75, w: 3.55, h: 2.85,
      barDir: "col", chartColors: [NARANJA, NARANJA, AQUA], varyColors: true,
      showTitle: true, title: "Cuánto empeoró el modelo (% de MAE)",
      titleFontFace: CUERPO, titleFontSize: 11, titleColor: BLANCO,
      showValue: true, dataLabelPosition: "outEnd",
      dataLabelFontFace: CUERPO, dataLabelFontSize: 10, dataLabelColor: BLANCO,
      dataLabelFormatCode: "+0.0;-0.0",
      showLegend: false,
      catAxisLabelColor: "AFC0D4", catAxisLabelFontFace: CUERPO, catAxisLabelFontSize: 10,
      valAxisLabelColor: "AFC0D4", valAxisLabelFontFace: CUERPO, valAxisLabelFontSize: 10,
      valGridLine: { color: "24374F", size: 1 },
      catGridLine: { style: "none" },
      valAxisMinVal: -20, valAxisMaxVal: 100, valAxisMajorUnit: 40,
      plotArea: { fill: { color: TINTA } }, chartArea: { fill: { color: TINTA } },
    }
  );

  tarjeta(s, M, 4.75, 7.3, 2.2, true);
  s.addText(
    "El lote 3 tiene un PSI de 3.265 —trece veces el umbral de alerta— y el " +
    "modelo acierta un 3.4% MEJOR que en validación.\n\n" +
    "Si el disparador mirara solo el drift, habríamos reentrenado un modelo que " +
    "estaba funcionando bien.",
    { x: M + 0.32, y: 4.95, w: 6.7, h: 1.9, fontFace: CUERPO, fontSize: 13, color: BLANCO, margin: 0, valign: "top" }
  );

  const dx = 8.35;
  s.addText("Por qué puede pasar", {
    x: dx, y: 1.75, w: 4.35, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: AQUA, margin: 0,
  });
  s.addText(
    [
      { text: "El modelo aprendió la relación entre las variables, no sus valores. Un invierno frío entra dentro de lo que ya sabe.", options: { bullet: true, breakLine: true } },
      { text: "El drift puede estar en variables que al modelo casi no le importan.", options: { bullet: true, breakLine: true } },
      { text: "Y al revés: se puede degradar sin drift ninguno. Eso es concept drift y el PSI no lo ve.", options: { bullet: true } },
    ],
    { x: dx, y: 2.2, w: 4.35, h: 2.6, fontFace: CUERPO, fontSize: 12.5, color: BLANCO, margin: 0, paraSpaceAfter: 8, valign: "top" }
  );

  tarjeta(s, dx, 4.75, 4.35, 2.2, true);
  s.addText(
    "El de datos avisa temprano, apenas llega el lote.\n\n" +
    "El de modelo confirma el daño, pero con horizonte de 24 horas solo se puede " +
    "medir un día después.",
    { x: dx + 0.3, y: 4.95, w: 3.75, h: 1.9, fontFace: CUERPO, fontSize: 12.5, color: BLANCO, margin: 0, valign: "top" }
  );

  s.addNotes(
    "Nicole. Esta es LA lamina del proyecto y responde la pregunta de la seccion Q " +
    "del enunciado. Que quede claro que no es teoria: son nuestros tres lotes. " +
    "batch1 +88.8%, batch2 +51.1%, batch3 -3.4%."
  );
}

// --------------------------------------------------------------------------
// 12 · Cuando reentrenar
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  titulo(s, "Cuándo reentrenar", 11);
  bajada(s, "Hacen falta las dos condiciones a la vez, no una sola");

  tarjeta(s, M, 1.85, 5.6, 1.85);
  s.addText(
    "SI    el PSI más alto ≥ 0.25\n" +
    "Y     el MAE empeoró más de 25%\n" +
    "Y     el lote trae ≥ 200 filas\n" +
    "ENTONCES  reentrenar",
    { x: M + 0.32, y: 2.05, w: 5.0, h: 1.5, fontFace: "Courier New", fontSize: 12.5, color: NEGRO, margin: 0, valign: "middle", lineSpacing: 19 }
  );

  const celdas = [
    ["REENTRENAR", "drift sí · degradación sí", "cambiaron los datos y el modelo lo sufrió", NARANJA],
    ["VIGILAR", "drift sí · degradación no", "cambiaron los datos pero el modelo aguanta", AZUL],
    ["REVISAR_DATOS", "drift no · degradación sí", "algo pasa que el PSI no ve", AZUL],
    ["TODO_BIEN", "drift no · degradación no", "seguir midiendo", AQUA],
  ];
  celdas.forEach((c, i) => {
    const x = M + (i % 2) * 2.9;
    const y = 4.0 + Math.floor(i / 2) * 1.5;
    tarjeta(s, x, y, 2.7, 1.35);
    s.addText(c[0], {
      x: x + 0.22, y: y + 0.14, w: 2.3, h: 0.3,
      fontFace: CUERPO, fontSize: 12.5, bold: true, color: c[3], margin: 0,
    });
    s.addText(c[1], {
      x: x + 0.22, y: y + 0.46, w: 2.3, h: 0.26,
      fontFace: CUERPO, fontSize: 10, color: GRIS, margin: 0,
    });
    s.addText(c[2], {
      x: x + 0.22, y: y + 0.72, w: 2.3, h: 0.55,
      fontFace: CUERPO, fontSize: 10.5, color: NEGRO, margin: 0, valign: "top",
    });
  });

  const dx = 6.6;
  s.addText("Lo que decidió con nuestros lotes", {
    x: dx, y: 2.05, w: 6.1, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: AZUL, margin: 0,
  });

  const filas = [
    ["batch1", "PSI 1.671", "+88.8%", "REENTRENAR", NARANJA],
    ["batch2", "PSI 6.175", "+51.1%", "REENTRENAR", NARANJA],
    ["batch3", "PSI 3.265", "−3.4%", "VIGILAR", AZUL],
  ];
  filas.forEach((f, i) => {
    const y = 2.55 + i * 0.72;
    tarjeta(s, dx, y, 6.1, 0.6);
    s.addText(f[0], { x: dx + 0.25, y, w: 1.1, h: 0.6, fontFace: CUERPO, fontSize: 12.5, bold: true, color: NEGRO, margin: 0, valign: "middle" });
    s.addText(f[1], { x: dx + 1.35, y, w: 1.5, h: 0.6, fontFace: CUERPO, fontSize: 12, color: GRIS, margin: 0, valign: "middle" });
    s.addText(f[2], { x: dx + 2.85, y, w: 1.2, h: 0.6, fontFace: CUERPO, fontSize: 12.5, bold: true, color: NEGRO, margin: 0, valign: "middle" });
    s.addText(f[3], { x: dx + 4.1, y, w: 1.85, h: 0.6, fontFace: CUERPO, fontSize: 12, bold: true, color: f[4], margin: 0, valign: "middle", align: "right" });
  });

  tarjeta(s, dx, 4.6, 6.1, 2.35);
  s.addText("El disparo no es automático, y es a propósito", {
    x: dx + 0.32, y: 4.8, w: 5.5, h: 0.34,
    fontFace: CUERPO, fontSize: 13.5, bold: true, color: NARANJA, margin: 0,
  });
  s.addText(
    "Cuando el sistema dice REENTRENAR queda registrado en el log y en el reporte, " +
    "pero el entrenamiento lo lanzamos nosotras.\n\n" +
    "Con un solo modelo y trece meses de historia, un reentrenamiento automático " +
    "puede reemplazar un modelo bueno por uno peor sin que nadie se entere.",
    { x: dx + 0.32, y: 5.22, w: 5.5, h: 1.7, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, valign: "top" }
  );

  s.addNotes(
    "Nicole. Si preguntan por que no automatizamos: no es que no supieramos " +
    "hacerlo, es una decision justificada por el tamano del historico. Con mas " +
    "datos y una comparacion previa contra el modelo vigente, si lo " +
    "automatizariamos."
  );
}

// --------------------------------------------------------------------------
// 13 · Pruebas y simulacion
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  titulo(s, "Pruebas y simulación de problemas", 12);
  bajada(s, "Fabricamos los defectos a propósito para comprobar que el sistema los agarra");

  const t = [
    ["19", "pruebas de variables\ny anti-leakage", AZUL],
    ["17", "pruebas de la API", AZUL],
    ["20", "pruebas del monitoreo", AQUA],
  ];
  t.forEach((c, i) => {
    const x = M + i * 2.05;
    tarjeta(s, x, 1.85, 1.9, 1.8);
    cifra(s, x, 2.0, 1.9, c[0], c[1], c[2]);
  });

  s.addText("56 pruebas, todas pasando", {
    x: M, y: 3.85, w: 5.9, h: 0.4,
    fontFace: TITULAR, fontSize: 18, bold: true, color: NEGRO, margin: 0,
  });
  s.addText(
    "La que más nos importa es test_no_reentrena_solo_por_drift: reproduce el caso " +
    "del lote 3 y falla si el sistema decidiera reentrenar. Si esa prueba se " +
    "pusiera en rojo, estaríamos botando modelos que funcionan.",
    { x: M, y: 4.32, w: 5.9, h: 1.1, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, valign: "top" }
  );

  tarjeta(s, M, 5.55, 5.9, 1.4);
  s.addText(
    "Las de leakage protegen la decisión de diseño más importante: comprueban " +
    "que ningún rezago menor que el horizonte pueda generarse.",
    { x: M + 0.3, y: 5.55, w: 5.3, h: 1.4, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, valign: "middle" }
  );

  const dx = 6.9;
  s.addText("Seis daños a una copia en memoria", {
    x: dx, y: 2.05, w: 5.8, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: AZUL, margin: 0,
  });
  s.addText(
    [
      { text: "faltantes · duplicados · valor absurdo", options: { breakLine: true } },
      { text: "tipo incorrecto · categoría desconocida · cambio de esquema", options: {} },
    ],
    { x: dx, y: 2.5, w: 5.8, h: 0.7, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, lineSpacing: 18, valign: "top" }
  );

  tarjeta(s, dx, 3.0, 5.8, 1.5);
  s.addText(
    "6 de 7 reglas fallaron  ·  pipeline bloqueado  ·  dataset intacto\n" +
    "el md5 del archivo original es el mismo antes y después",
    { x: dx + 0.3, y: 3.15, w: 5.2, h: 1.2, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, valign: "middle" }
  );

  tarjeta(s, dx, 4.7, 5.8, 2.25);
  s.addShape(pres.ShapeType.ellipse, { x: dx + 0.3, y: 4.92, w: 0.4, h: 0.4, fill: { color: NARANJA } });
  s.addText("!", {
    x: dx + 0.3, y: 4.92, w: 0.4, h: 0.4,
    align: "center", valign: "middle", fontFace: CUERPO, fontSize: 15, bold: true, color: BLANCO, margin: 0,
  });
  s.addText("Encontró un error real en nuestro código", {
    x: dx + 0.85, y: 4.92, w: 4.7, h: 0.4,
    fontFace: CUERPO, fontSize: 13.5, bold: true, color: NARANJA, margin: 0, valign: "middle",
  });
  s.addText(
    "La regla R05 se caía cuando le llegaba texto donde esperaba un número. Sin " +
    "esta simulación, ese error habría aparecido el día que un sensor mandara " +
    "texto por un fallo de formato, y en producción, no en una prueba.",
    { x: dx + 0.3, y: 5.45, w: 5.2, h: 1.4, fontFace: CUERPO, fontSize: 12.5, color: NEGRO, margin: 0, valign: "top" }
  );

  s.addNotes(
    "Nicole. Contar el error de R05 sin adornos: lo encontramos nosotras, lo " +
    "corregimos y quedo la prueba. Eso vale mas que decir que todo salio bien a la " +
    "primera."
  );
}

// --------------------------------------------------------------------------
// 14 · Limites
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  titulo(s, "Qué no hicimos, y qué haríamos con más tiempo", 13);
  bajada(s, "Ser honestas sobre los límites es parte del trabajo");

  s.addText("Los límites de este trabajo", {
    x: M, y: 1.85, w: 5.9, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: NARANJA, margin: 0,
  });
  s.addText(
    [
      { text: "Un solo lugar y un solo año: una ciudad del norte de Italia, 2004-2005.", options: { bullet: true, breakLine: true } },
      { text: "Trece meses es poco para una serie estacional: solo vimos un invierno.", options: { bullet: true, breakLine: true } },
      { text: "El umbral del 25% de degradación lo escogimos nosotras, no salió de datos del negocio.", options: { bullet: true, breakLine: true } },
      { text: "Los umbrales del PSI vienen prestados del riesgo crediticio.", options: { bullet: true, breakLine: true } },
      { text: "El modelo no explica pronósticos individuales.", options: { bullet: true } },
    ],
    { x: M, y: 2.28, w: 5.9, h: 3.3, fontFace: CUERPO, fontSize: 13, color: NEGRO, margin: 0, paraSpaceAfter: 8, valign: "top" }
  );

  const dx = 6.9;
  s.addText("Lo que seguiría, en orden de valor", {
    x: dx, y: 1.85, w: 5.8, h: 0.34,
    fontFace: CUERPO, fontSize: 14, bold: true, color: AQUA, margin: 0,
  });
  s.addText(
    [
      { text: "Conseguir más años de datos. Es lo que más movería la aguja.", options: { bullet: true, breakLine: true } },
      { text: "Fijar el umbral de degradación con datos del negocio.", options: { bullet: true, breakLine: true } },
      { text: "Reentrenamiento automático, pero comparando el candidato contra el modelo vigente antes de reemplazarlo.", options: { bullet: true, breakLine: true } },
      { text: "Explicabilidad por pronóstico, para justificar una alerta concreta.", options: { bullet: true, breakLine: true } },
      { text: "Que las alertas salgan del log y le lleguen a alguien.", options: { bullet: true } },
    ],
    { x: dx, y: 2.28, w: 5.8, h: 3.3, fontFace: CUERPO, fontSize: 13, color: NEGRO, margin: 0, paraSpaceAfter: 8, valign: "top" }
  );

  s.addNotes(
    "Mayarling. Esta lamina suele gustar en una defensa: demuestra que sabemos " +
    "donde estan los limites y que no estamos vendiendo el trabajo por mas de lo " +
    "que es."
  );
}

// --------------------------------------------------------------------------
// 15 · Demo
// --------------------------------------------------------------------------
{
  const s = pres.addSlide();
  laminaOscura(s);
  titulo(s, "Demostración en vivo", 14, { claro: true, chapa: AQUA });
  bajada(s, "El recorrido completo, de los datos crudos a la alerta", { claro: true });

  const pasos = [
    ["Raw Data", "python -m src.ingestion.ingest"],
    ["Validation", "python -m src.validation.diagnose"],
    ["Training", "python -m src.training.train"],
    ["MLflow", "mlflow ui"],
    ["Model Registry", "alias candidato y produccion"],
    ["Docker", "docker run -p 8000:8000 grupo8-mlops"],
    ["API Prediction", "python scripts/probar_api.py"],
    ["Monitoring", "python -m src.monitoring.run_monitoring"],
    ["Drift Alert", "python -m src.monitoring.contaminar"],
  ];

  pasos.forEach((p, i) => {
    const col = Math.floor(i / 5);
    const fil = i % 5;
    const x = M + col * 6.35;
    const y = 1.85 + fil * 1.02;

    s.addShape(pres.ShapeType.ellipse, { x, y: y + 0.1, w: 0.4, h: 0.4, fill: { color: i === 8 ? NARANJA : AZUL } });
    s.addText(String(i + 1), {
      x, y: y + 0.1, w: 0.4, h: 0.4,
      align: "center", valign: "middle", fontFace: CUERPO, fontSize: 12, bold: true, color: BLANCO, margin: 0,
    });
    s.addText(p[0], {
      x: x + 0.55, y, w: 5.4, h: 0.36,
      fontFace: CUERPO, fontSize: 13.5, bold: true, color: BLANCO, margin: 0, valign: "middle",
    });
    s.addText(p[1], {
      x: x + 0.55, y: y + 0.34, w: 5.4, h: 0.32,
      fontFace: "Courier New", fontSize: 10, color: "9EE8C8", margin: 0, valign: "middle",
    });
  });

  tarjeta(s, M + 6.35, 4.95, 5.75, 1.9, true);
  s.addText("Si nos pasan un lote que no hemos visto", {
    x: M + 6.67, y: 5.13, w: 5.1, h: 0.34,
    fontFace: CUERPO, fontSize: 13, bold: true, color: NARANJA, margin: 0,
  });
  s.addText(
    "Pasa por los mismos Data Quality Gates. Si está bien, sale el pronóstico y " +
    "el PSI contra la referencia. Si está roto, el pipeline se detiene y dice qué " +
    "regla falló y por qué.",
    { x: M + 6.67, y: 5.55, w: 5.1, h: 1.2, fontFace: CUERPO, fontSize: 12, color: "AFC0D4", margin: 0, valign: "top" }
  );

  s.addNotes(
    "Las dos. Tener el contenedor ya levantado ANTES de empezar la defensa, para " +
    "no perder tiempo esperando. Si el profesor pasa un lote nuevo, el guion esta " +
    "en presentacion/guion_demo.md."
  );
}

// --------------------------------------------------------------------------
pres.writeFile({ fileName: path.join(__dirname, "grupo8_mlops.pptx") })
  .then((f) => console.log("Presentacion guardada en " + f));

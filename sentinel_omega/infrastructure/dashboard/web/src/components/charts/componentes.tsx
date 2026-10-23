/**
 * Puente de charts/componentes → Sparkline canónico.
 *
 * La reestructuración duplicó las primitivas de gráfica aquí con props
 * traducidos al español (datos/claveClave/altura) y bugs (un `<div>`
 * cerrado con `</button>`, `puntos` sin declarar, `altura` como propiedad
 * CSS). Los dos únicos consumidores (SeñalesTab, CimaticaTab) usan
 * SimpleBars — y el import de SeñalesTab estaba muerto. Este shim deja
 * UNA sola implementación: la de charts/Sparkline, verificada contra
 * producción desde el 2026-09-28.
 */
export { SimpleBars, LineSpark, SimplePie } from "@/components/charts/Sparkline";

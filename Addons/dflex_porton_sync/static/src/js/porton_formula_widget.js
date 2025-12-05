/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";

export class PortonFormulaJSField extends CharField {
    /**
     * Cuando el usuario escribe en el input, guardamos la fórmula
     * y calculamos el nuevo valor en base al campo base_value.
     */
    async onInput(ev) {
        // Llamamos al comportamiento estándar para actualizar formula_js
        await super.onInput(ev);

        const formula = ev.target.value;
        const base = this.props.record.data.base_value;

        if (!formula || base === undefined || base === null) {
            return;
        }

        let result = null;
        try {
            // Definimos la variable 'valor' para que la fórmula la pueda usar.
            const valor = base;
            // PELIGRO: eval ejecuta código arbitrario. Esto está pensado
            // solo para usuarios internos de confianza.
            // eslint-disable-next-line no-eval
            result = eval(formula);
        } catch (e) {
            console.error("Error evaluando fórmula JS", e);
            return;
        }

        if (typeof result === "number" && !isNaN(result)) {
            // Actualizamos el campo computed_value en el registro
            this.props.record.update({ computed_value: result });
        }
    }
}

PortonFormulaJSField.template = "dflex_porton_sync.PortonFormulaJSField";

registry.category("fields").add("porton_formula_js", PortonFormulaJSField);
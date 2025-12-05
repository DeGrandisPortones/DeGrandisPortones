/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";

export class PortonFormulaJSField extends CharField {
    async onInput(ev) {
        await super.onInput(ev);

        const formula = ev.target.value;
        const base = this.props.record.data.base_value;

        if (!formula || base === undefined || base === null) {
            return;
        }

        let result = null;
        try {
            const valor = base;
            // eslint-disable-next-line no-eval
            result = eval(formula);
        } catch (e) {
            console.error("Error evaluando fórmula JS", e);
            return;
        }

        if (typeof result === "number" && !isNaN(result)) {
            this.props.record.update({ computed_value: result });
        }
    }
}

PortonFormulaJSField.template = "dflex_porton_sync.PortonFormulaJSField";

registry.category("fields").add("porton_formula_js", PortonFormulaJSField);
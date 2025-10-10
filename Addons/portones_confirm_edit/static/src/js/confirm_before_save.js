/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const TARGET_MODEL = "x_dflex.porton";

function ask(env, title, body) {
    return new Promise((resolve) => {
        env.services.dialog.add(ConfirmationDialog, {
            title,
            body,
            confirm: () => resolve(true),
            cancel: () => resolve(false),
        });
    });
}

/**
 * FORM: confirmar al entrar en edición y al guardar
 */
patch(FormController.prototype, "portones_confirm_edit.form_confirmations_scoped", {
    async onEdit() {
        const resModel = this.model?.root?.resModel;
        if (resModel !== TARGET_MODEL) {
            return this._super(...arguments);
        }
        const ok = await ask(
            this.env,
            this.env._t("Habilitar edición"),
            this.env._t("¿Querés editar este registro de Portones?")
        );
        if (!ok) return;
        return this._super(...arguments);
    },

    async save(recordID) {
        const resModel = this.model?.root?.resModel;
        if (resModel !== TARGET_MODEL) {
            return this._super(...arguments);
        }
        const ok = await ask(
            this.env,
            this.env._t("Confirmar guardado"),
            this.env._t("¿Deseás guardar los cambios en este registro de Portones?")
        );
        if (!ok) return false;
        return this._super(...arguments);
    },
});

/**
 * LIST: confirmar al guardar cambios inline (editable="top/bottom")
 */
patch(ListController.prototype, "portones_confirm_edit.list_confirm_on_save_scoped", {
    async saveButtonClicked() {
        const resModel = this.model?.root?.resModel;
        if (resModel !== TARGET_MODEL) {
            return this._super(...arguments);
        }
        const ok = await ask(
            this.env,
            this.env._t("Confirmar guardado"),
            this.env._t("¿Deseás guardar los cambios en esta fila de Portones?")
        );
        if (!ok) return; // cancelar guardado inline
        return this._super(...arguments);
    },
});

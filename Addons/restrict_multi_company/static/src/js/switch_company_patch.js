/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { CompanySelector } from "@web/webclient/switch_company_menu/switch_company_menu";
import { session } from "@web/session";

patch(CompanySelector.prototype, {
    switchCompany(mode, companyId) {
        // El usuario Administrator (id=2) puede combinar empresas libremente
        if (session.uid === 2) {
            return super.switchCompany(mode, companyId);
        }

        if (mode === "toggle") {
            if (this.selectedCompaniesIds.includes(companyId)) {
                // No permitir deseleccionar si es la única empresa activa
                if (this.selectedCompaniesIds.length > 1) {
                    this._deselectCompany(companyId);
                }
            } else {
                // Deseleccionar todas y activar solo la empresa elegida
                this.selectedCompaniesIds.splice(0, this.selectedCompaniesIds.length);
                this._selectCompany(companyId);
            }
        } else if (mode === "loginto") {
            // "Entrar como" → siempre una sola empresa activa
            this.selectedCompaniesIds.splice(0, this.selectedCompaniesIds.length);
            this._selectCompany(companyId, true);
            this.apply();
            this.dropdownState.close?.();
        }
    },
});

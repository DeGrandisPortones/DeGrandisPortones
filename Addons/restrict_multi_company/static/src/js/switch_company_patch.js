/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { cookie } from "@web/core/browser/cookie";
import { router } from "@web/core/browser/router";
import { companyService } from "@web/webclient/company_service";
import { CompanySelector } from "@web/webclient/switch_company_menu/switch_company_menu";

// Todos los usuarios, sin excepción, trabajan con una sola empresa activa.

// "1-2" (cookie/URL actual), "1,2" (URLs viejas) o 1 -> primera empresa
function primeraEmpresa(cids) {
    return Number(String(cids).split(/[-,]/)[0]);
}

patch(companyService, {
    start(env, services) {
        // Al cargar la página Odoo toma las empresas activas de la URL o de la
        // cookie `cids`, que es una sola para todas las pestañas. Pueden venir
        // dos empresas (pestañas de distintas empresas que se pisan la cookie
        // al recargar después de un deploy, links de mails, URLs viejas):
        // dejamos solo la primera.
        const state = router.current;
        if ("cids" in state) {
            state.cids = primeraEmpresa(state.cids);
        }
        const cookieCids = cookie.get("cids");
        if (cookieCids && /[-,]/.test(cookieCids)) {
            cookie.set("cids", String(primeraEmpresa(cookieCids)));
        }

        const service = super.start(...arguments);
        const setCompanies = service.setCompanies;
        service.setCompanies = function (companyIds) {
            // Además del menú, Odoo cambia las empresas activas solo: al abrir un
            // registro de otra empresa la SUMA a las activas (form_controller).
            // Siempre nos quedamos con una: la última, que es la recién agregada.
            const companyId = companyIds[companyIds.length - 1];
            return setCompanies.call(this, companyId ? [companyId] : [], false);
        };
        return service;
    },
});

patch(CompanySelector.prototype, {
    switchCompany(mode, companyId) {
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

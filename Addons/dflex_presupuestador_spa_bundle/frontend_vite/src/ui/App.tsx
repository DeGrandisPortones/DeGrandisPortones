import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api";

type Rubro = { id: number; name: string; qty_mode: "m2" | "one" | "manual" };
type PedidoRow = {
  id: number;
  name: string;
  state: string;
  coeficiente: number;
  m2: number;
  amount_total: number;
  currency_symbol: string;
};
type PedidoDetail = {
  id: number;
  name: string;
  state: string;
  coeficiente: number;
  sistema?: string;
  ancho?: number;
  alto?: number;
  peso_m2?: number;
  m2: number;
  peso_total: number;
  totals?: { untaxed: number; tax: number; total: number; currency_symbol: string };
  lines?: Array<{
    id: number;
    rubro: { id: number; name: string };
    product: { id: number; name: string };
    qty: number;
    precio_distr: number;
    price_unit: number;
    price_total: number;
    obs?: string;
  }>;
};

function fmt(n: number) {
  const v = Number.isFinite(n) ? n : 0;
  return (Math.round((v + Number.EPSILON) * 100) / 100).toLocaleString("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function safeTotals(pedido: PedidoDetail | null, currencySymbol: string) {
  const t = pedido?.totals;
  return {
    untaxed: t?.untaxed ?? 0,
    tax: t?.tax ?? 0,
    total: t?.total ?? 0,
    currency_symbol: t?.currency_symbol ?? currencySymbol,
  };
}

export default function App() {
  const [session, setSession] = useState<any>(null);
  const [rubros, setRubros] = useState<Rubro[]>([]);
  const [pedidos, setPedidos] = useState<PedidoRow[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [pedido, setPedido] = useState<PedidoDetail | null>(null);

  // Add line form
  const [rubroId, setRubroId] = useState<number | null>(null);
  const [productos, setProductos] = useState<Array<{ id: number; name: string; uom: string }>>([]);
  const [productoId, setProductoId] = useState<number | null>(null);
  const [qty, setQty] = useState<number>(1);
  const [obs, setObs] = useState<string>("");

  const currency = session?.currency?.symbol ?? "$";

  async function refreshList() {
    const rows = await api.pedidos();
    setPedidos(Array.isArray(rows) ? rows : []);
  }

  async function loadPedido(id: number) {
    const d: any = await api.getPedido(id);

    // Manejo de errores del backend (devuelve {error: ...})
    if (!d || d.error) {
      console.error("getPedido error:", d);
      alert(`No se pudo cargar el presupuesto: ${d?.error ?? "unknown_error"}`);
      return;
    }

    // Defaults defensivos para evitar crashes
    const normalized: PedidoDetail = {
      ...d,
      totals: d.totals || { untaxed: 0, tax: 0, total: 0, currency_symbol: currency },
      lines: Array.isArray(d.lines) ? d.lines : [],
    };

    setPedido(normalized);
    setSelectedId(id);
  }

  useEffect(() => {
    (async () => {
      const s = await api.session();
      setSession(s);

      const r = await api.rubros();
      setRubros(Array.isArray(r) ? r : []);
      setRubroId(Array.isArray(r) && r.length ? r[0].id : null);

      await refreshList();
    })().catch((e) => {
      console.error(e);
      alert(String(e?.message || e));
    });
  }, []);

  useEffect(() => {
    (async () => {
      if (!rubroId) {
        setProductos([]);
        setProductoId(null);
        return;
      }
      const prods = await api.productos({ rubro_id: rubroId, limit: 80 });
      const arr = Array.isArray(prods) ? prods : [];
      setProductos(arr);
      setProductoId(arr.length ? arr[0].id : null);
    })().catch((e) => {
      console.error(e);
      alert(String(e?.message || e));
    });
  }, [rubroId]);

  const selectedRubro = useMemo(() => {
    return Array.isArray(rubros) ? rubros.find((r) => r.id === rubroId) ?? null : null;
  }, [rubros, rubroId]);

  async function onCreate() {
    const coef = 25;
    const res: any = await api.crearPedido(coef);
    if (!res || res.error) {
      alert(`No se pudo crear: ${res?.error ?? "unknown_error"}`);
      return;
    }
    await refreshList();
    await loadPedido(res.id);
  }

  async function onSaveHeader(values: any) {
    if (!pedido) return;
    const res: any = await api.updatePedido(pedido.id, values);
    if (res?.error) {
      alert(`No se pudo guardar: ${res.error}`);
      return;
    }
    await loadPedido(pedido.id);
  }

  async function onAddLine() {
    if (!pedido || !rubroId || !productoId) return;
    const res: any = await api.addLinea({
      pedido_id: pedido.id,
      rubro_id: rubroId,
      product_id: productoId,
      qty,
      obs,
    });

    if (res?.error) {
      alert(`No se pudo agregar: ${res.error}`);
      return;
    }

    setObs("");
    setQty(1);
    await loadPedido(pedido.id);
  }

  async function onDeleteLine(line_id: number) {
    if (!pedido) return;
    const res: any = await api.delLinea(pedido.id, line_id);
    if (res?.error) {
      alert(`No se pudo eliminar: ${res.error}`);
      return;
    }
    await loadPedido(pedido.id);
  }

  const totals = safeTotals(pedido, currency);

  return (
    <div className="container">
      <div className="flex-between">
        <div>
          <div className="h1">Presupuestador</div>
          <div className="muted">
            Usuario: {session?.user?.name ?? "—"} | Partner: {session?.partner?.name ?? "—"} | Lista:{" "}
            {session?.pricelist?.name ?? "—"}
          </div>
        </div>
        <div className="flex">
          <button className="secondary" onClick={() => (window.location.href = "/my")}>
            Portal
          </button>
          <button onClick={onCreate}>Nuevo presupuesto</button>
        </div>
      </div>

      <div className="row" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="flex-between" style={{ marginBottom: 10 }}>
            <div>
              <strong>Mis presupuestos</strong>
              <div className="muted">Abrí uno para editarlo</div>
            </div>
            <button className="secondary" onClick={refreshList}>
              Refrescar
            </button>
          </div>

          <table className="table">
            <thead>
              <tr>
                <th>Nro</th>
                <th className="right">Total</th>
              </tr>
            </thead>
            <tbody>
              {pedidos.map((p) => (
                <tr key={p.id} style={{ cursor: "pointer" }} onClick={() => loadPedido(p.id)}>
                  <td>
                    <div className="flex-between">
                      <div>
                        <div>
                          <strong>{p.name}</strong>
                        </div>
                        <div className="muted">
                          Coef: {fmt(p.coeficiente)}% · m²: {fmt(p.m2)}
                        </div>
                      </div>
                      <span className="badge">{p.state}</span>
                    </div>
                  </td>
                  <td className="right">
                    <strong>
                      {fmt(p.amount_total)} {p.currency_symbol}
                    </strong>
                  </td>
                </tr>
              ))}
              {!pedidos.length && (
                <tr>
                  <td colSpan={2} className="muted">
                    Sin presupuestos todavía.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="card">
          {!pedido ? (
            <div className="muted">Seleccioná un presupuesto para empezar.</div>
          ) : (
            <>
              <div className="flex-between">
                <div>
                  <div className="h1" style={{ fontSize: 18 }}>
                    {pedido.name}
                  </div>
                  <div className="muted">Estado: {pedido.state}</div>
                </div>
                <div className="flex">
                  <button
                    className="secondary"
                    onClick={() =>
                      window.open(
                        `/report/pdf/dflex_presupuestador_spa.report_presupuestador_pedido/${pedido.id}`,
                        "_blank"
                      )
                    }
                  >
                    PDF
                  </button>
                </div>
              </div>

              <hr />

              <div className="grid2">
                <div>
                  <label>Sistema</label>
                  <input
                    defaultValue={pedido.sistema ?? ""}
                    onBlur={(e) => onSaveHeader({ sistema: e.target.value })}
                    placeholder="Ej: ACERO SIMIL ALUMINIO..."
                  />
                </div>
                <div>
                  <label>Coeficiente (%)</label>
                  <input
                    defaultValue={pedido.coeficiente}
                    type="number"
                    step="0.01"
                    onBlur={(e) => onSaveHeader({ coeficiente: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label>Ancho (m)</label>
                  <input
                    defaultValue={pedido.ancho ?? 0}
                    type="number"
                    step="0.01"
                    onBlur={(e) => onSaveHeader({ ancho: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label>Alto (m)</label>
                  <input
                    defaultValue={pedido.alto ?? 0}
                    type="number"
                    step="0.01"
                    onBlur={(e) => onSaveHeader({ alto: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label>Peso (kg/m²)</label>
                  <input
                    defaultValue={pedido.peso_m2 ?? 0}
                    type="number"
                    step="0.01"
                    onBlur={(e) => onSaveHeader({ peso_m2: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label>Calculados</label>
                  <input value={`m²: ${fmt(pedido.m2)} | kg: ${fmt(pedido.peso_total)}`} readOnly />
                </div>
              </div>

              <hr />

              <div className="flex-between">
                <div>
                  <strong>Agregar ítem</strong>
                  <div className="muted">
                    Rubro: {selectedRubro?.name ?? "—"} ({selectedRubro?.qty_mode ?? "—"})
                  </div>
                </div>
              </div>

              <div className="grid2" style={{ marginTop: 10 }}>
                <div>
                  <label>Rubro</label>
                  <select value={rubroId ?? ""} onChange={(e) => setRubroId(Number(e.target.value))}>
                    {rubros.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label>Producto</label>
                  <select value={productoId ?? ""} onChange={(e) => setProductoId(Number(e.target.value))}>
                    {productos.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label>Cantidad (solo si rubro manual)</label>
                  <input value={qty} onChange={(e) => setQty(Number(e.target.value))} type="number" step="0.01" />
                </div>
                <div>
                  <label>Observación</label>
                  <input value={obs} onChange={(e) => setObs(e.target.value)} placeholder="Opcional" />
                </div>
              </div>

              <div style={{ marginTop: 10 }}>
                <button onClick={onAddLine}>Agregar</button>
              </div>

              <hr />

              <div className="flex-between">
                <strong>Detalle</strong>
                <div className="muted">
                  Subtotal: {fmt(totals.untaxed)} {currency} · IVA: {fmt(totals.tax)} {currency} · Total:{" "}
                  <strong>
                    {fmt(totals.total)} {currency}
                  </strong>
                </div>
              </div>

              <table className="table" style={{ marginTop: 10 }}>
                <thead>
                  <tr>
                    <th>Rubro / Producto</th>
                    <th className="right">Cant.</th>
                    <th className="right">Base</th>
                    <th className="right">Precio</th>
                    <th className="right">Total</th>
                    <th className="right"></th>
                  </tr>
                </thead>
                <tbody>
                  {(pedido.lines ?? []).map((l) => (
                    <tr key={l.id}>
                      <td>
                        <div className="muted">{l.rubro.name}</div>
                        <div>
                          <strong>{l.product.name}</strong>
                        </div>
                        {l.obs ? <div className="muted">{l.obs}</div> : null}
                      </td>
                      <td className="right">{fmt(l.qty)}</td>
                      <td className="right">{fmt(l.precio_distr)}</td>
                      <td className="right">{fmt(l.price_unit)}</td>
                      <td className="right">
                        <strong>{fmt(l.price_total)}</strong>
                      </td>
                      <td className="right">
                        <button className="danger" onClick={() => onDeleteLine(l.id)}>
                          X
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!(pedido.lines ?? []).length && (
                    <tr>
                      <td colSpan={6} className="muted">
                        Sin ítems.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

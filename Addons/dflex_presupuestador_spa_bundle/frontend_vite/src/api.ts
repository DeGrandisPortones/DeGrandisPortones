type Json = any;

async function post<T = Json>(url: string, payload: any = {}): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // Important for Odoo session cookie
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export const api = {
  session: () => post("/api/presupuestador/session", {}),
  rubros: () => post("/api/presupuestador/rubros", {}),
  productos: (params: { rubro_id?: number; q?: string; limit?: number }) => post("/api/presupuestador/productos", params),
  pedidos: () => post("/api/presupuestador/pedidos", {}),
  crearPedido: (coeficiente: number) => post("/api/presupuestador/pedidos/create", { coeficiente }),
  getPedido: (pedido_id: number) => post("/api/presupuestador/pedidos/get", { pedido_id }),
  updatePedido: (pedido_id: number, values: any) => post("/api/presupuestador/pedidos/update", { pedido_id, values }),
  addLinea: (args: { pedido_id: number; rubro_id: number; product_id: number; qty?: number; obs?: string }) =>
    post("/api/presupuestador/lineas/add", args),
  delLinea: (pedido_id: number, line_id: number) => post("/api/presupuestador/lineas/delete", { pedido_id, line_id }),
};

type Json = any;

type JsonRpcResponse<T = any> = {
  jsonrpc?: string;
  id?: number | string;
  result?: T;
  error?: {
    code?: number;
    message?: string;
    data?: {
      message?: string;
      debug?: string;
      name?: string;
    };
  };
};

async function post<T = Json>(url: string, params: any = {}): Promise<T> {
  const rpcPayload = {
    jsonrpc: "2.0",
    method: "call",
    params,
    id: Date.now(),
  };

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(rpcPayload),
  });

  const data: JsonRpcResponse<T> = await res.json();

  // Odoo JSON-RPC standard
  if (data?.error) {
    const msg =
      data.error?.data?.message ||
      data.error?.message ||
      "RPC error";
    throw new Error(msg);
  }

  if (Object.prototype.hasOwnProperty.call(data, "result")) {
    return data.result as T;
  }

  // Fallback (por si algún endpoint devuelve JSON plano)
  return data as unknown as T;
}

export const api = {
  session: () => post("/api/presupuestador/session", {}),
  rubros: () => post("/api/presupuestador/rubros", {}),
  productos: (params: { rubro_id?: number; q?: string; limit?: number }) =>
    post("/api/presupuestador/productos", params),

  pedidos: () => post("/api/presupuestador/pedidos", {}),

  crearPedido: (coeficiente: number) =>
    post("/api/presupuestador/pedidos/create", { coeficiente }),

  getPedido: (pedido_id: number) =>
    post("/api/presupuestador/pedidos/get", { pedido_id }),

  updatePedido: (pedido_id: number, values: any) =>
    post("/api/presupuestador/pedidos/update", { pedido_id, values }),

  addLinea: (args: {
    pedido_id: number;
    rubro_id: number;
    product_id: number;
    qty?: number;
    obs?: string;
  }) => post("/api/presupuestador/lineas/add", args),

  delLinea: (pedido_id: number, line_id: number) =>
    post("/api/presupuestador/lineas/delete", { pedido_id, line_id }),
};

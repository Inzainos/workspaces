import { useState } from "react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Tabla de datos. Cifras en tabular-nums y alineadas a la derecha cuando la
 * columna se marca numérica: una columna de números centrada o ragged no se
 * puede comparar de un vistazo, que es justo para lo que existe esta tabla.
 */
export function DataTable({
  columns,
  rows,
  empty = "Sin datos en DB",
  pageSize = 15,
  densa = false,
}: {
  columns: {
    key: string;
    label: string;
    num?: boolean;
    render?: (row: Record<string, unknown>, value: unknown) => ReactNode;
  }[];
  rows: Record<string, unknown>[];
  empty?: string;
  pageSize?: number;
  densa?: boolean;
}) {
  const [page, setPage] = useState(0);
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const p = Math.min(page, totalPages - 1);
  const paginated = rows.slice(p * pageSize, (p + 1) * pageSize);

  if (!rows.length) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-surface-sunken/60 px-4 py-8 text-center text-meta text-muted">
        {empty}
      </div>
    );
  }

  const pad = densa ? "px-2.5 py-1" : "px-3 py-1.5";

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full border-collapse text-body">
          <thead>
            <tr className="bg-surface-sunken">
              {columns.map((c) => (
                <th
                  key={c.key}
                  className={cn(
                    "etiqueta whitespace-nowrap border-b border-border font-medium",
                    pad,
                    c.num ? "text-right" : "text-left",
                  )}
                >
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.map((row, i) => (
              <tr
                key={i}
                className="border-b border-border/60 transition-colors last:border-0 hover:bg-surface-raised/60"
              >
                {columns.map((c) => (
                  <td
                    key={c.key}
                    className={cn(
                      "whitespace-nowrap text-body",
                      pad,
                      c.num ? "mono text-right tabular-nums" : "",
                    )}
                  >
                    {c.render ? (
                      c.render(row, row[c.key])
                    ) : row[c.key] === null || row[c.key] === undefined || row[c.key] === "" ? (
                      <span className="dato-ausente">—</span>
                    ) : (
                      String(row[c.key])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-meta text-muted">
          <span className="mono">
            {p * pageSize + 1}–{Math.min((p + 1) * pageSize, rows.length)} de{" "}
            {rows.length.toLocaleString("es-MX")}
          </span>
          <div className="flex gap-1.5">
            <button
              onClick={() => setPage(Math.max(0, p - 1))}
              disabled={p === 0}
              className="rounded border border-border px-2.5 py-1 transition-colors hover:bg-surface-raised disabled:opacity-40"
            >
              Anterior
            </button>
            <button
              onClick={() => setPage(Math.min(totalPages - 1, p + 1))}
              disabled={p === totalPages - 1}
              className="rounded border border-border px-2.5 py-1 transition-colors hover:bg-surface-raised disabled:opacity-40"
            >
              Siguiente
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

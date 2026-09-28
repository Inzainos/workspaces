import { useState } from "react";
import { api } from "@/lib/api";

/**
 * Consulta al Concilio (modelos locales con lectura de la DB).
 *
 * Sin marco propio: vive dentro de un `Panel`, y anidar dos bordes crea la
 * caja-dentro-de-caja que enturbia la jerarquía del tablero.
 */
export function AskBox() {
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  async function ask() {
    const question = q.trim();
    if (!question) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.ask(question);
      setAnswer(String(res.answer || "Sin respuesta."));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-2.5">
      <div className="flex gap-2">
        <input
          className="flex-1 rounded-md border border-border bg-[color:var(--color-base-900)] px-3 py-2 text-body text-foreground placeholder:text-faint"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="¿Cómo va el Fantasma hoy?"
          aria-label="Pregunta al Concilio"
          onKeyDown={(e) => {
            if (e.key === "Enter") void ask();
          }}
        />
        <button
          type="button"
          className="shrink-0 rounded-md border border-border px-3.5 py-2 text-body font-medium text-body transition-colors hover:bg-surface-raised disabled:opacity-50"
          onClick={() => void ask()}
          disabled={loading}
        >
          {loading ? "Consultando…" : "Preguntar"}
        </button>
      </div>
      {error ? (
        <p className="text-meta" style={{ color: "var(--color-aviso)" }}>
          {error}
        </p>
      ) : null}
      {answer ? (
        <div className="rounded-md border border-border bg-surface-sunken/60 px-3 py-2.5 text-body leading-relaxed text-body whitespace-pre-wrap">
          {answer}
        </div>
      ) : null}
    </div>
  );
}

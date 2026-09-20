import { useState } from "react";
import { api } from "@/lib/api";

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
    <section className="rounded-lg border border-border bg-card/40 p-3 space-y-2">
      <div className="text-sm font-medium">Preguntar al resumen operativo</div>
      <div className="flex gap-2">
        <input
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ej: ¿cómo va Fantasma hoy?"
          onKeyDown={(e) => {
            if (e.key === "Enter") void ask();
          }}
        />
        <button
          type="button"
          className="rounded-md border border-border px-3 py-2 text-sm hover:bg-card"
          onClick={() => void ask()}
          disabled={loading}
        >
          {loading ? "Consultando…" : "Preguntar"}
        </button>
      </div>
      {error ? <div className="text-xs text-warning">{error}</div> : null}
      {answer ? <div className="text-sm text-foreground whitespace-pre-wrap">{answer}</div> : null}
    </section>
  );
}

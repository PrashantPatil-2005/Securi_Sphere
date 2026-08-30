"use client";

import { memo, useMemo, useState, useCallback } from "react";
import { ChevronDown, ChevronRight, Copy, Check } from "lucide-react";

interface EventRawJsonProps {
  data: string | null;
  label?: string;
}

function formatJson(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function JsonValue({ value }: { value: unknown }): React.ReactNode {
  if (value === null || value === undefined) {
    return <span className="text-muted italic">null</span>;
  }
  if (typeof value === "boolean") {
    return <span className="text-accent">{String(value)}</span>;
  }
  if (typeof value === "number") {
    return <span className="text-severity-high">{value}</span>;
  }
  if (typeof value === "string") {
    return <span className="text-severity-low">{value}</span>;
  }
  if (Array.isArray(value)) {
    return <span className="text-muted">[{value.length} items]</span>;
  }
  return <span className="text-muted">{JSON.stringify(value)}</span>;
}

function JsonKey({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-severity-medium font-medium">
      {children}
      <span className="text-muted">: </span>
    </span>
  );
}

function CollapsibleJson({ label, data, depth = 0 }: { label: string; data: unknown; depth?: number }) {
  const [expanded, setExpanded] = useState(depth < 3);

  const entries = useMemo(() => {
    if (data === null || data === undefined) return [];
    if (typeof data === "object" && !Array.isArray(data)) return Object.entries(data as Record<string, unknown>);
    if (Array.isArray(data)) return (data as unknown[]).map((v, i) => [String(i), v] as const);
    return [];
  }, [data]);

  if (entries.length === 0) return null;

  return (
    <div className={depth > 0 ? "ml-3 border-l border-border-subtle pl-2" : ""}>
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex items-center gap-1.5 w-full text-xs font-medium text-foreground hover:text-accent transition-colors text-left py-0.5"
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3 text-muted shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 text-muted shrink-0" />
        )}
        <JsonKey>{label}</JsonKey>
        <span className="text-muted tabular-nums">{entries.length} keys</span>
      </button>
      {expanded && (
        <div className="font-mono text-xs leading-relaxed">
          {entries.map(([key, value]) => (
            <div key={key} className="flex gap-0 py-0.5">
              {typeof value === "object" && value !== null ? (
                <CollapsibleJson label={key} data={value} depth={depth + 1} />
              ) : (
                <span>
                  <JsonKey>{key}</JsonKey>
                  <JsonValue value={value} />
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EventRawJsonInner({ data, label = "Raw Log" }: EventRawJsonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    if (!data) return;
    navigator.clipboard.writeText(data).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [data]);

  if (!data) {
    return (
      <div className="text-xs text-muted italic py-2">No raw log available</div>
    );
  }

  const parsed = formatJson(data);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted uppercase tracking-wide">{label}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 text-xs text-muted hover:text-foreground transition-colors"
          aria-label="Copy raw log"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-success" />
              <span className="text-success">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {parsed !== null ? (
        <div className="border border-border-subtle rounded-lg overflow-hidden bg-card">
          <div className="p-3 font-mono text-xs leading-relaxed max-h-80 overflow-y-auto">
            {typeof parsed === "object" && parsed !== null ? (
              <CollapsibleJson label="root" data={parsed} />
            ) : (
              <pre className="whitespace-pre-wrap break-words">{String(parsed)}</pre>
            )}
          </div>
        </div>
      ) : (
        <div className="border border-border-subtle rounded-lg overflow-hidden bg-card">
          <pre className="p-3 font-mono text-xs leading-relaxed max-h-80 overflow-y-auto whitespace-pre-wrap break-words text-muted">
            {data}
          </pre>
        </div>
      )}
    </div>
  );
}

export const EventRawJson = memo(EventRawJsonInner);

/** Normalize API list responses (paginated `{ items, total }` or legacy plain arrays). */
export function parsePaginatedList<T>(
  r: { items?: T[]; total?: number; next_cursor?: string | null; has_more?: boolean } | T[] | null | undefined,
): { items: T[]; total: number; next_cursor: string | null; has_more: boolean } {
  if (Array.isArray(r)) {
    return { items: r, total: r.length, next_cursor: null, has_more: false };
  }
  const items = r?.items ?? [];
  return {
    items,
    total: r?.total ?? items.length,
    next_cursor: r?.next_cursor ?? null,
    has_more: r?.has_more ?? false,
  };
}

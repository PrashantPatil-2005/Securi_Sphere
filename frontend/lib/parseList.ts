/** Normalize API list responses (paginated `{ items, total }` or legacy plain arrays). */
export function parsePaginatedList<T>(
  r: { items?: T[]; total?: number } | T[] | null | undefined,
): { items: T[]; total: number } {
  if (Array.isArray(r)) {
    return { items: r, total: r.length };
  }
  const items = r?.items ?? [];
  return { items, total: r?.total ?? items.length };
}

/** Stable row-key helpers — avoid inline lambdas that break memoized table children. */
export function rowKeyById<T extends { id: string }>(row: T): string {
  return row.id;
}

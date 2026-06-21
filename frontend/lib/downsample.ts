/** Downsample time-series points for chart rendering without losing shape. */
export function downsampleSeries<T>(points: T[], maxPoints = 120): T[] {
  if (points.length <= maxPoints) return points;
  const step = Math.ceil(points.length / maxPoints);
  const sampled: T[] = [];
  for (let i = 0; i < points.length; i += step) sampled.push(points[i]);
  const last = points[points.length - 1];
  if (sampled[sampled.length - 1] !== last) sampled.push(last);
  return sampled;
}

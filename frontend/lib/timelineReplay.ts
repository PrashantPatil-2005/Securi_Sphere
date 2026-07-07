export const REPLAY_SPEEDS = [0.5, 1, 2, 4] as const;
export type ReplaySpeed = (typeof REPLAY_SPEEDS)[number];

const MIN_STEP_MS = 350;
const MAX_STEP_MS = 6000;

/** Milliseconds to wait before showing event[i] after event[i-1] during replay. */
export function replayStepDelayMs(
  prevTimestamp: string,
  nextTimestamp: string,
  speed: ReplaySpeed,
): number {
  const delta = new Date(nextTimestamp).getTime() - new Date(prevTimestamp).getTime();
  const scaled = delta > 0 ? delta / speed : 1200 / speed;
  return Math.round(Math.min(Math.max(scaled, MIN_STEP_MS), MAX_STEP_MS));
}

export function replayProgress(currentIndex: number, total: number): number {
  if (total <= 1) return total === 1 ? 100 : 0;
  return Math.round((currentIndex / (total - 1)) * 100);
}

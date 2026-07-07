export const ONBOARDING_DISMISSED_KEY = "securi_onboarding_done";
export const ONBOARDING_SEARCH_KEY = "securi_onboarding_search";

export function markOnboardingSearchCompleted(): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ONBOARDING_SEARCH_KEY, "1");
  window.dispatchEvent(new Event("securi-onboarding-update"));
}

export function isOnboardingSearchCompleted(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(ONBOARDING_SEARCH_KEY) === "1";
}

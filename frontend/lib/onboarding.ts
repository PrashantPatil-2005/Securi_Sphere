export const ONBOARDING_DISMISSED_KEY = "securi_onboarding_done";
export const ONBOARDING_WIZARD_DISMISSED_KEY = "securi_onboarding_wizard_done";
export const ONBOARDING_SEARCH_KEY = "securi_onboarding_search";

export function isOnboardingWizardDismissed(): boolean {
  if (typeof window === "undefined") return true;
  return localStorage.getItem(ONBOARDING_WIZARD_DISMISSED_KEY) === "1";
}

export function dismissOnboardingWizard(): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ONBOARDING_WIZARD_DISMISSED_KEY, "1");
}

export function reopenOnboardingWizard(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ONBOARDING_WIZARD_DISMISSED_KEY);
  window.dispatchEvent(new Event("securi-onboarding-wizard-open"));
}

export function markOnboardingSearchCompleted(): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ONBOARDING_SEARCH_KEY, "1");
  window.dispatchEvent(new Event("securi-onboarding-update"));
}

export function isOnboardingSearchCompleted(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(ONBOARDING_SEARCH_KEY) === "1";
}

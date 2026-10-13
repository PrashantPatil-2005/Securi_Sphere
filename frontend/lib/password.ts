/**
 * Client-side mirror of the backend password policy
 * (backend/app/schemas/auth.py `_PASSWORD_COMPLEXITY`).
 * Keep both in sync: >=8 chars with uppercase, lowercase, digit and special char.
 */
const SPECIAL_CHARS = "!@#$%^&*()_+-=[]{};':\"\\|,.<>/?";

export const PASSWORD_POLICY_MESSAGE =
  "Password must be at least 8 characters and include uppercase, lowercase, digit, and special character";

export function passwordPolicyError(password: string): string | null {
  if (password.length < 8) return "Password must be at least 8 characters";
  const hasSpecial = Array.from(password).some((c) => SPECIAL_CHARS.includes(c));
  if (!hasSpecial || !/[a-z]/.test(password) || !/[A-Z]/.test(password) || !/[0-9]/.test(password)) {
    return PASSWORD_POLICY_MESSAGE;
  }
  return null;
}

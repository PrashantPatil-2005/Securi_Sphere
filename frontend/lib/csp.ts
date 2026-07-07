const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function connectSrc(): string {
  const parts = ["'self'"];
  try {
    const url = new URL(API_URL);
    parts.push(url.origin);
    const wsProto = url.protocol === "https:" ? "wss:" : "ws:";
    parts.push(`${wsProto}//${url.host}`);
  } catch {
    parts.push("ws://localhost:8000", "http://localhost:8000");
  }
  return parts.join(" ");
}

export function createNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

export function buildContentSecurityPolicy(nonce: string, dev = process.env.NODE_ENV === "development"): string {
  const scriptSrc = dev
    ? "'self' 'unsafe-eval' 'unsafe-inline'"
    : `'self' 'nonce-${nonce}' 'strict-dynamic'`;
  const styleSrc = dev ? "'self' 'unsafe-inline'" : `'self' 'nonce-${nonce}'`;

  const directives = [
    "default-src 'self'",
    `script-src ${scriptSrc}`,
    `style-src ${styleSrc}`,
    "img-src 'self' data: blob:",
    "font-src 'self'",
    `connect-src ${connectSrc()}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ];

  const reportUri = process.env.CSP_REPORT_URI;
  if (reportUri) {
    directives.push(`report-uri ${reportUri}`);
  }

  return directives.join("; ");
}

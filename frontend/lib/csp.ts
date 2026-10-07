const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function addBackendOrigins(target: Set<string>, httpOrigin: string) {
  target.add(httpOrigin);
  try {
    const url = new URL(httpOrigin);
    const wsProto = url.protocol === "https:" ? "wss:" : "ws:";
    target.add(`${wsProto}//${url.host}`);
  } catch {
    /* ignore invalid URL */
  }
}

function connectSrc(pageHostname?: string): string {
  const origins = new Set<string>(["'self'"]);

  addBackendOrigins(origins, API_URL);
  addBackendOrigins(origins, "http://localhost:8000");
  addBackendOrigins(origins, "http://127.0.0.1:8000");

  if (pageHostname && pageHostname !== "localhost" && pageHostname !== "127.0.0.1") {
    addBackendOrigins(origins, `http://${pageHostname}:8000`);
  }

  return Array.from(origins).join(" ");
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

export function buildContentSecurityPolicy(
  nonce: string,
  dev = process.env.NODE_ENV === "development",
  pageHostname?: string,
): string {
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
    `connect-src ${connectSrc(pageHostname)}`,
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

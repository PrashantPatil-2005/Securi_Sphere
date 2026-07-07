import Link from "next/link";
import { FileQuestion } from "lucide-react";

export default function NotFound() {
  return (
    <div className="ambient-bg min-h-screen flex items-center justify-center p-6">
      <div className="max-w-md w-full glass-panel p-8 text-center space-y-4">
        <div className="flex justify-center">
          <FileQuestion className="w-12 h-12 text-muted" aria-hidden />
        </div>
        <h1 className="text-display text-foreground">Page not found</h1>
        <p className="text-body text-muted">
          The page you requested does not exist or was moved.
        </p>
        <Link href="/" className="btn-primary inline-flex items-center px-4 py-2">
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}

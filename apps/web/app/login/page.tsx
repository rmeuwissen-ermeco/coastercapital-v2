import { Suspense } from "react";

import { LoginForm } from "@/components/login-form";

export default function LoginPage() {
  return (
    <main className="login-shell">
      <Suspense fallback={<p>Loading secure sign-in…</p>}>
        <LoginForm />
      </Suspense>
    </main>
  );
}

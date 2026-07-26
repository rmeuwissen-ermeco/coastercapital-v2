"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  async function login(event: FormEvent) {
    event.preventDefault();
    setMessage("Signing in…");
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      setMessage(data?.detail ?? "Could not sign in");
      return;
    }
    const destination = searchParams.get("next");
    router.replace(destination?.startsWith("/admin") ? destination : "/admin");
    router.refresh();
  }

  return (
    <form className="login-card" onSubmit={login}>
      <span className="brand-mark" aria-hidden="true">
        C
      </span>
      <p className="label-large">SECURE ADMIN</p>
      <h1>Sign in</h1>
      <p>Use your Coaster Capital administrator account.</p>
      <label>
        Email
        <input
          autoComplete="email"
          onChange={(event) => setEmail(event.target.value)}
          required
          type="email"
          value={email}
        />
      </label>
      <label>
        Password
        <input
          autoComplete="current-password"
          minLength={12}
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
      </label>
      <button className="filled-button" type="submit">
        Sign in
      </button>
      <span className="form-message" aria-live="polite">
        {message}
      </span>
    </form>
  );
}

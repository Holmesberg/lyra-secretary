"use client";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export function ConsentModal({ onAccepted }: { onAccepted: () => void }) {
  const [terms, setTerms] = useState(false);
  const [research, setResearch] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!terms) {
      setError("You must accept the Terms and Privacy Policy to use Barzakh.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api("/v1/users/me/consent", {
        method: "POST",
        body: JSON.stringify({ terms_accepted: terms, research_consent: research }),
      });
      onAccepted();
    } catch (e: any) {
      setError(e.message || "Failed to save consent.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50">
      <div
        className="bg-background border border-border rounded-lg max-w-lg w-full p-6"
        onKeyDown={(e) => {
          if (e.key !== "Enter") return;
          if (e.shiftKey || e.ctrlKey || e.metaKey || e.altKey) return;
          if ((e.target as HTMLElement).tagName === "TEXTAREA") return;
          if (!terms || submitting) return;
          e.preventDefault();
          submit();
        }}
      >
        <h2 className="text-xl font-semibold mb-2">Before you continue</h2>
        <p className="text-muted-foreground text-sm mb-6">
          Barzakh learns from how you plan and work to personalize your scheduler. Please review and accept.
        </p>

        <label className="flex items-start gap-3 mb-4 cursor-pointer">
          <input
            type="checkbox"
            checked={terms}
            onChange={(e) => setTerms(e.target.checked)}
            className="mt-1"
          />
          <span className="text-sm">
            I accept the{" "}
            <Link href="/terms" target="_blank" className="underline">Terms of Service</Link>{" "}
            and{" "}
            <Link href="/privacy" target="_blank" className="underline">Privacy Policy</Link>.{" "}
            <span className="text-muted-foreground">(required)</span>
          </span>
        </label>

        <label className="flex items-start gap-3 mb-6 cursor-pointer">
          <input
            type="checkbox"
            checked={research}
            onChange={(e) => setResearch(e.target.checked)}
            className="mt-1"
          />
          <span className="text-sm">
            I allow my anonymized usage data to be used to improve Barzakh over time.{" "}
            <span className="text-muted-foreground">(optional)</span>
          </span>
        </label>

        {error && <p className="text-sm text-ember mb-4">{error}</p>}

        <button
          onClick={submit}
          disabled={submitting || !terms}
          className="w-full px-4 py-2 rounded-sm bg-parchment text-void font-medium hover:bg-parchment/90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {submitting ? "Saving…" : "Continue"}
        </button>
      </div>
    </div>
  );
}

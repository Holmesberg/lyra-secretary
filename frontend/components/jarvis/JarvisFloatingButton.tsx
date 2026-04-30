"use client";
/**
 * Lyra assistant launcher — floating action button + global Alt+L shortcut.
 *
 * Renders only when the parent passes `enabled={true}` (which the parent
 * decides from `me.is_operator`). Backend also enforces the operator gate
 * via 403 on /v1/jarvis/* (endpoint paths kept Jarvis-named for stable
 * implementation; user-facing copy is Lyra), so the worst case for a UI
 * bug here is a useless button that returns 403 when clicked.
 *
 * The pulse-glow color is driven by the NIM health probe — cyan when
 * NIM is reachable, ember when it's down or rate-limited. Probe runs
 * once on mount + whenever the modal opens (cheap heartbeat against
 * the 40 RPM free-tier ceiling).
 */
import { useEffect, useState } from "react";
import { jarvisHealth } from "@/lib/jarvis";
import { JarvisChatModal } from "./JarvisChatModal";

interface Props {
  enabled: boolean;
}

// Alt+L chosen over Ctrl+L (browser address bar) and Ctrl+J (Downloads).
// Browser-level shortcuts run BEFORE page handlers — preventDefault on
// the page can't suppress them. Alt+L is unbound across Chrome, Edge,
// and Firefox on Windows; mnemonic for Lyra.
function detectShortcutLabel(): string {
  if (typeof navigator === "undefined") return "Alt+L";
  const platform = navigator.platform || "";
  const ua = navigator.userAgent || "";
  return /Mac|iPhone|iPad/.test(platform) || /Mac OS/.test(ua) ? "⌥+L" : "Alt+L";
}

export function JarvisFloatingButton({ enabled }: Props) {
  const [open, setOpen] = useState(false);
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const [healthReason, setHealthReason] = useState<string | null>(null);
  const [shortcutLabel, setShortcutLabel] = useState("Alt+L");

  useEffect(() => {
    setShortcutLabel(detectShortcutLabel());
  }, []);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    async function probe() {
      try {
        const h = await jarvisHealth();
        if (!cancelled) {
          setHealthy(h.available);
          setHealthReason(h.reason);
        }
      } catch {
        if (!cancelled) {
          setHealthy(false);
          setHealthReason("network");
        }
      }
    }
    probe();
    return () => {
      cancelled = true;
    };
  }, [enabled, open]);

  useEffect(() => {
    if (!enabled) return;
    function onKey(e: KeyboardEvent) {
      // Alt+L on Windows/Linux, Option+L on Mac. Either modifier
      // triggers — keeps the binding consistent across platforms.
      const isAltL = e.altKey && e.key.toLowerCase() === "l";
      if (isAltL) {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled, open]);

  if (!enabled) return null;

  const ringColor = healthy
    ? "border-signal/60 shadow-[0_0_24px_rgba(0,229,255,0.45)] hover:bg-signal/15"
    : healthy === false
      ? "border-ember/60 shadow-[0_0_18px_rgba(255,107,71,0.35)] hover:bg-ember/15"
      : "border-hairline-signal/40";
  const dotColor = healthy
    ? "bg-signal"
    : healthy === false
      ? "bg-ember"
      : "bg-dust";

  const tooltip = healthy
    ? `Lyra · ${shortcutLabel}`
    : healthy === false
      ? `Lyra offline${healthReason ? ` (${healthReason})` : ""}`
      : "Lyra · checking";

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        title={tooltip}
        aria-label={tooltip}
        className={`fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full border-2 bg-void-2/80 backdrop-blur-md transition-all hover:scale-105 ${ringColor}`}
      >
        <span className="font-mono text-[11px] font-semibold tracking-widest text-parchment">
          L
        </span>
        <span
          className={`absolute -bottom-1 -right-1 h-3 w-3 rounded-full border-2 border-void ${dotColor}`}
        />
      </button>
      <JarvisChatModal open={open} onClose={() => setOpen(false)} />
    </>
  );
}

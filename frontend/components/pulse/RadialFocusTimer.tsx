"use client";
/**
 * RadialFocusTimer — the wow component. Big SVG arc with the elapsed
 * time at the center, glow effect, breathing animation when active.
 *
 * Modeled on the reference image: cyan radial progress, mono digits,
 * Neural Noir restraint. State-aware:
 *   - Idle: dimmed track, "Ready when you are" copy, 00:00.
 *   - Active: cyan arc fills clockwise as elapsed/planned grows.
 *     Subtle pulse-glow on the arc.
 *   - Paused: ember-toned arc + freeze.
 *   - Overflow (elapsed > planned): ember neon arc, "+Nm past planned"
 *     copy.
 */
import { useEffect, useRef, useState } from "react";
import type { StopwatchStatus } from "@/lib/tasks";
import { getElapsedSeconds } from "@/lib/stopwatch-time";

export interface RadialFocusTimerProps {
  status: StopwatchStatus | undefined;
  /** Diameter in pixels. Default 280 — reference image proportions. */
  size?: number;
}

function pad2(n: number): string {
  return n.toString().padStart(2, "0");
}

function fmtElapsed(totalSeconds: number): { primary: string; suffix: string } {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h > 0) {
    return { primary: `${h}:${pad2(m)}`, suffix: pad2(s) };
  }
  return { primary: `${pad2(m)}`, suffix: pad2(s) };
}

export function RadialFocusTimer({ status, size = 280 }: RadialFocusTimerProps) {
  const stroke = 10;
  const radius = (size - stroke * 2 - 12) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * radius;

  // Wall-clock-derived elapsed for sub-second accuracy between server
  // refetches. The query elsewhere refetches every 5s, but the digits
  // need to move every second.
  const baseSecondsRef = useRef(0);
  const baseAtRef = useRef<number>(Date.now());
  const [, forceTick] = useState(0);

  useEffect(() => {
    if (!status?.active || status.paused) return;
    baseSecondsRef.current = getElapsedSeconds(status);
    baseAtRef.current = Date.now();
    const id = setInterval(() => forceTick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, [status?.active, status?.paused, status?.elapsed_seconds]);

  const isActive = !!status?.active;
  const isPaused = !!status?.paused;
  const liveSeconds =
    isActive && !isPaused
      ? baseSecondsRef.current +
        Math.floor((Date.now() - baseAtRef.current) / 1000)
      : getElapsedSeconds(status);
  const planned = (status?.planned_duration_minutes ?? 0) * 60;
  const overflow = isActive && planned > 0 ? Math.max(0, liveSeconds - planned) : 0;
  const isOverflow = overflow > 0;

  const progressPct =
    isActive && planned > 0
      ? Math.min(1, liveSeconds / planned)
      : 0;
  const dashOffset = circumference * (1 - progressPct);

  const { primary, suffix } = fmtElapsed(isActive ? liveSeconds : 0);

  // Color scheme by state.
  const arcStart = isOverflow
    ? "#FF8A3D"
    : isPaused
      ? "#F5A96A"
      : "#4DD4E8";
  const arcEnd = isOverflow
    ? "#F5A96A"
    : isPaused
      ? "#F5A96A"
      : "#00E5FF";
  const glowColor = isOverflow
    ? "rgba(255,138,61,0.55)"
    : isPaused
      ? "rgba(245,169,106,0.45)"
      : "rgba(0,229,255,0.55)";
  const trackColor = isActive
    ? "rgba(77,212,232,0.08)"
    : "rgba(74,81,104,0.18)";

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      {/* Outer atmospheric glow — soft halo behind the arc. */}
      {isActive && (
        <div
          aria-hidden
          className="absolute inset-0 rounded-full opacity-60 blur-2xl"
          style={{
            background: `radial-gradient(circle, ${glowColor} 0%, transparent 65%)`,
          }}
        />
      )}

      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="relative"
      >
        <defs>
          <linearGradient id="focusArcGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={arcStart} />
            <stop offset="100%" stopColor={arcEnd} />
          </linearGradient>
          {/* Subtle radial gradient for inner depth. */}
          <radialGradient id="focusInnerGlow" cx="50%" cy="50%" r="50%">
            <stop offset="60%" stopColor="rgba(20,27,42,0)" />
            <stop offset="100%" stopColor="rgba(77,212,232,0.06)" />
          </radialGradient>
        </defs>
        {/* Inner depth glow */}
        <circle cx={cx} cy={cy} r={radius - stroke / 2} fill="url(#focusInnerGlow)" />
        {/* Track */}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="none"
          stroke={trackColor}
          strokeWidth={stroke}
        />
        {/* Progress arc */}
        {isActive && (
          <circle
            cx={cx}
            cy={cy}
            r={radius}
            fill="none"
            stroke="url(#focusArcGradient)"
            strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            transform={`rotate(-90 ${cx} ${cy})`}
            style={{
              filter: `drop-shadow(0 0 14px ${glowColor})`,
              transition: "stroke-dashoffset 0.95s linear, stroke 200ms",
            }}
            className={!isPaused && !isOverflow ? "animate-pulse-glow" : ""}
          />
        )}
        {/* Tick marks at quarter rotations — subtle reference points */}
        {[0, 90, 180, 270].map((deg) => {
          const rad = ((deg - 90) * Math.PI) / 180;
          const inner = radius - stroke / 2 - 4;
          const outer = radius + stroke / 2 + 4;
          const x1 = cx + inner * Math.cos(rad);
          const y1 = cy + inner * Math.sin(rad);
          const x2 = cx + outer * Math.cos(rad);
          const y2 = cy + outer * Math.sin(rad);
          return (
            <line
              key={deg}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="rgba(77,212,232,0.18)"
              strokeWidth={1}
            />
          );
        })}
      </svg>

      {/* Center stack — primary digits + label. */}
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <div className="flex items-baseline">
          <span
            className={`font-display font-semibold leading-none tabular-nums ${
              isOverflow
                ? "neon-ember"
                : isPaused
                  ? "text-ember"
                  : isActive
                    ? "neon-cyan"
                    : "text-dust-deep"
            }`}
            style={{
              fontSize: size * 0.22,
              letterSpacing: "-0.04em",
            }}
          >
            {primary}
          </span>
          <span
            className={`font-display font-semibold leading-none tabular-nums ${
              isOverflow
                ? "text-ember/80"
                : isPaused
                  ? "text-ember/80"
                  : isActive
                    ? "text-signal/85"
                    : "text-dust-deep/70"
            }`}
            style={{
              fontSize: size * 0.12,
              letterSpacing: "-0.03em",
              marginLeft: "0.1em",
            }}
          >
            :{suffix}
          </span>
        </div>
        <div className="mt-2 font-display text-[10px] font-medium uppercase tracking-macro text-dust">
          {isOverflow
            ? `+${Math.floor(overflow / 60)}m past planned`
            : isPaused
              ? "Paused"
              : isActive && planned > 0
                ? `of ${Math.floor(planned / 60)}m planned`
                : isActive
                  ? "Focus session"
                  : "No session running"}
        </div>
      </div>
    </div>
  );
}

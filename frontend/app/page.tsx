// Server component — renders the full landing SSR so crawlers see all
// copy as real HTML text instead of the previous client-only
// "Loading…" skeleton. Auth-redirect for authenticated visitors lives
// in the tiny client <AuthRedirectGate /> below.

import { SiteNav } from "@/components/landing/site-nav";
import { StarField } from "@/components/landing/star-field";
import { CircuitBg } from "@/components/landing/circuit-bg";
import { Hero } from "@/components/landing/hero";
import { ThesisSection } from "@/components/landing/thesis-section";
import { FeaturedInsight } from "@/components/landing/featured-insight";
import { InstrumentGrid } from "@/components/landing/instrument-grid";
import { LiveDataStrip } from "@/components/landing/live-data-strip";
import { ManifestoPreview } from "@/components/landing/manifesto-preview";
import { DeployCta } from "@/components/landing/deploy-cta";
import { SiteFooter } from "@/components/landing/site-footer";
import { AuthRedirectGate } from "@/components/landing/auth-redirect-gate";

export default function LandingPage() {
  return (
    <main className="relative isolate min-h-screen overflow-hidden bg-neural-void text-parchment">
      <AuthRedirectGate />

      {/* Layered atmosphere: stars (depth) + circuit substrate (cyber texture)
          + warm amber radial glow in the top-right corner for warmth. */}
      <StarField />
      <div className="pointer-events-none fixed inset-0 -z-10 text-signal">
        <CircuitBg />
      </div>
      <div
        aria-hidden
        className="pointer-events-none fixed right-0 top-0 -z-10 h-[600px] w-[600px] translate-x-[25%] -translate-y-[25%]"
        style={{
          background:
            "radial-gradient(circle at center, rgba(245, 169, 106, 0.1) 0%, rgba(245, 169, 106, 0.05) 35%, transparent 70%)",
        }}
      />

      <SiteNav />
      <Hero />
      <ThesisSection />
      <FeaturedInsight />
      <InstrumentGrid />
      <LiveDataStrip />
      <ManifestoPreview />
      <DeployCta />
      <SiteFooter />
    </main>
  );
}

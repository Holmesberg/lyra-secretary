"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { SiteNav } from "@/components/landing/site-nav";
import { StarField } from "@/components/landing/star-field";
import { Hero } from "@/components/landing/hero";
import { ThesisSection } from "@/components/landing/thesis-section";
import { InstrumentGrid } from "@/components/landing/instrument-grid";
import { LiveDataStrip } from "@/components/landing/live-data-strip";
import { ManifestoPreview } from "@/components/landing/manifesto-preview";
import { DeployCta } from "@/components/landing/deploy-cta";
import { SiteFooter } from "@/components/landing/site-footer";

export default function LandingPage() {
  const { status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") router.replace("/today");
  }, [status, router]);

  useEffect(() => {
    document.body.setAttribute("data-surface", "landing");
    return () => document.body.removeAttribute("data-surface");
  }, []);

  if (status === "loading" || status === "authenticated") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-void text-xs text-dust">
        Loading…
      </div>
    );
  }

  return (
    <main className="relative isolate min-h-screen overflow-hidden bg-lyra-night text-parchment">
      <StarField />
      <SiteNav />
      <Hero />
      <ThesisSection />
      <InstrumentGrid />
      <LiveDataStrip />
      <ManifestoPreview />
      <DeployCta />
      <SiteFooter />
    </main>
  );
}

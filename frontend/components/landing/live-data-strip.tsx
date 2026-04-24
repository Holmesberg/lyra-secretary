"use client";

import { AreaChart, BarChart, DonutChart } from "@tremor/react";
import { CornerMarks } from "./corner-marks";

const deltaSeries = [
  { session: "s1", "delta (min)": 42 },
  { session: "s5", "delta (min)": 38 },
  { session: "s10", "delta (min)": 31 },
  { session: "s15", "delta (min)": 24 },
  { session: "s20", "delta (min)": 19 },
  { session: "s25", "delta (min)": 14 },
  { session: "s30", "delta (min)": 11 },
  { session: "s35", "delta (min)": 8 },
  { session: "s40", "delta (min)": 6 },
  { session: "s45", "delta (min)": 3 },
];

const biasByCategory = [
  { category: "health", "bias factor": 2.0 },
  { category: "dev", "bias factor": 1.5 },
  { category: "work", "bias factor": 1.3 },
  { category: "exercise", "bias factor": 1.0 },
  { category: "academic", "bias factor": 1.1 },
];

const pauseDistribution = [
  { reason: "low focus", value: 35 },
  { reason: "distraction", value: 25 },
  { reason: "task difficulty", value: 15 },
  { reason: "external", value: 10 },
  { reason: "intentional break", value: 10 },
  { reason: "prayer", value: 5 },
];

const initiationPattern = [
  { window: "w1", initiated: 4, retroactive: 2, abandoned: 1 },
  { window: "w2", initiated: 7, retroactive: 2, abandoned: 0 },
  { window: "w3", initiated: 9, retroactive: 3, abandoned: 1 },
  { window: "w4", initiated: 12, retroactive: 2, abandoned: 0 },
];

export function LiveDataStrip() {
  return (
    <section id="live-data" className="relative border-y border-hairline bg-void-2/30 py-24 md:py-32">
      <div className="mx-auto max-w-5xl px-6 md:px-10">
        <div className="mx-auto max-w-2xl text-center">
          <p className="mb-6 font-mono text-[11px] uppercase tracking-widest text-signal">
            <span className="text-signal/60">//</span> live from operative-001
          </p>
          <h2 className="font-display text-4xl font-medium leading-[1.1] tracking-tight text-parchment md:text-5xl">
            Four patterns, one{" "}
            <span className="neon-cyan">baseline</span>.
          </h2>
          <p className="mx-auto mt-5 max-w-lg text-sm leading-relaxed text-dust md:text-base">
            Every bar, curve, and slice below is the operator&apos;s real
            data. No synthetic fixtures. No seed content.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-5 sm:grid-cols-2">
          <ChartCell code="03.1" label="Delta (planned − executed)" caption="trending toward zero — learning">
            <AreaChart
              data={deltaSeries}
              index="session"
              categories={["delta (min)"]}
              colors={["cyan"]}
              showLegend={false}
              showGridLines={false}
              showYAxis
              yAxisWidth={36}
              className="mt-4 h-44"
              curveType="monotone"
            />
          </ChartCell>

          <ChartCell code="03.2" label="Bias factor by category" caption="health 2.0× plan · academic ~1.1×">
            <BarChart
              data={biasByCategory}
              index="category"
              categories={["bias factor"]}
              colors={["amber"]}
              showLegend={false}
              showGridLines={false}
              yAxisWidth={36}
              className="mt-4 h-44"
            />
          </ChartCell>

          <ChartCell code="03.3" label="Pause reason distribution" caption="35% low focus · 25% distraction">
            <DonutChart
              data={pauseDistribution}
              category="value"
              index="reason"
              colors={["cyan", "amber", "rose", "violet", "orange", "sky"]}
              showLabel={false}
              className="mt-4 h-44"
            />
          </ChartCell>

          <ChartCell code="03.4" label="Initiation status by week" caption="more sessions logged real-time, fewer retroactive">
            <BarChart
              data={initiationPattern}
              index="window"
              categories={["initiated", "retroactive", "abandoned"]}
              colors={["cyan", "amber", "rose"]}
              stack
              showLegend
              showGridLines={false}
              yAxisWidth={36}
              className="mt-4 h-44"
            />
          </ChartCell>
        </div>
      </div>
    </section>
  );
}

function ChartCell({
  code,
  label,
  caption,
  children,
}: {
  code: string;
  label: string;
  caption: string;
  children: React.ReactNode;
}) {
  return (
    <div className="relative">
      <CornerMarks size={8} thickness={1} color="rgba(77, 212, 232, 0.4)" />
      <div className="terminal-panel h-full p-6">
        <div className="flex items-baseline justify-between">
          <p className="font-mono text-[10px] uppercase tracking-widest text-signal">
            :: {code}
          </p>
          <p className="font-mono text-[10px] uppercase tracking-widest text-dust">
            {label}
          </p>
        </div>
        {children}
        <p className="mt-4 font-mono text-[10px] uppercase tracking-widest text-dust-deep">
          {caption}
        </p>
      </div>
    </div>
  );
}

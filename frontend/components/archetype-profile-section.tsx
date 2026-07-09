"use client";
/**
 * Archetype profile section — persistent Settings surface.
 *
 * Replaces the original retrofit banner (2026-04-22 operator feedback:
 * "allow button in settings to try later, allow retry for users who
 * already entered once after 3 months"). Always visible; copy and
 * button prominence vary by user state.
 *
 * 2026-04-26 (LYR-112): the label is now session-gated. The survey
 * captures a single moment of the user (could be finals stress, sleep
 * deprivation, etc.) — naming an archetype before LyraOS has watched the
 * user actually work overfits transient state into something that reads
 * as identity. MANIFESTO §VT-25 + docs/building_phases.md:167 specify
 * sessions 5-7 as the reveal threshold; below that we show "settling
 * in" copy and hide the label entirely. The bias_factor blend still
 * uses the prior internally — we just don't surface the name.
 *
 * States handled (in priority order):
 *
 *   1. NO ASSIGNMENT
 *      → "Help LyraOS start with a sense of how you work — 4-min survey"
 *      → Primary [Take survey]
 *
 *   2. SKIPPED (completed=False, defaulted to Diffuse Average)
 *      → "LyraOS's using a generic starting point until you take it"
 *      → Primary [Take survey]
 *
 *   3. CALIBRATING (assigned, but executed_session_count < 5)
 *      → "Settling in. After ~N more sessions LyraOS will share a profile
 *         that reflects how you actually work."
 *      → Secondary [Retake survey]
 *      → Label hidden (this is the LYR-112 gate; applies even to users
 *        who completed the survey, which is the whole point)
 *
 *   4. RECENT (assigned, ≥5 sessions, <90 days)
 *      → "Profile: <label> · early read"
 *      → Body warmly notes the label may shift
 *      → Secondary [Retake survey]
 *
 *   5. AGED (≥90 days)
 *      → "Profile: <label>" + "It's been a while — your rhythm may have
 *         shifted. Take the survey again to refresh things."
 *      → Primary [Retake survey]
 *
 * Research note: re-takes write NEW ArchetypeAssignment rows
 * (submit_archetype_survey is additive). The original assignment
 * stays in history for longitudinal stability analysis (Gate 5).
 * User.archetype_id flips to the latest assignment's archetype_id,
 * which is what the Rule-13 blend reads.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArchetypeSurvey } from "@/components/archetype-survey";
import {
  ARCHETYPE_LABELS,
  getArchetypeProximity,
  getArchetypeProximityTrend,
} from "@/lib/archetype";
import {
  ArchetypeProximityRows,
  ArchetypeSaturationNote,
  ArchetypeTrendCaption,
} from "@/components/archetype-proximity-display";

const NINETY_DAYS_MS = 90 * 24 * 60 * 60 * 1000;

// MANIFESTO.md:810 — "display archetype at session 5–7 with
// medium-confidence framing". 5 is the floor; below this the label is
// hidden because the survey-based archetype hasn't been validated
// against any actual behavior yet. The bias_factor blend still uses
// the prior internally; it's only the visible label that's gated.
const ARCHETYPE_REVEAL_MIN_SESSIONS = 5;

export interface ArchetypeProfileSectionProps {
  /** Current archetype_id from /me. Null when no assignment exists. */
  archetypeId: string | null;
  /** True only if the user has a completed=True ArchetypeAssignment. */
  completed: boolean;
  /** ISO timestamp of the latest assignment (completed OR skipped). */
  latestAssignmentAt: string | null;
  /** Total EXECUTED, non-voided sessions ever. Drives the label gate. */
  executedSessionCount: number;
  /** Called after survey submit / skip — parent refetches /me. */
  onChanged: () => void;
}

type SectionState = "no_assignment" | "skipped" | "calibrating" | "recent" | "aged";

export function ArchetypeProfileSection({
  archetypeId,
  completed,
  latestAssignmentAt,
  executedSessionCount,
  onChanged,
}: ArchetypeProfileSectionProps) {
  const [surveyOpen, setSurveyOpen] = useState(false);

  const state = classifyState(
    completed,
    latestAssignmentAt,
    executedSessionCount
  );
  const daysSince = latestAssignmentAt
    ? Math.floor(
        (Date.now() - new Date(latestAssignmentAt).getTime()) /
          (24 * 60 * 60 * 1000)
      )
    : null;

  const label = archetypeId
    ? ARCHETYPE_LABELS[archetypeId] ?? archetypeId
    : null;

  const sessionsToReveal = Math.max(
    0,
    ARCHETYPE_REVEAL_MIN_SESSIONS - executedSessionCount
  );

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Your profile</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 p-4 pt-0">
          {state === "no_assignment" && (
            <StatePanel
              emphasis="primary"
              heading="No profile yet"
              body="A 4-minute survey gives LyraOS a head start — morning
                vs evening person, how you tend to approach things.
                After a few sessions together, LyraOS refines this from
                how you actually move through your day."
              buttonLabel="Take the survey"
              onClick={() => setSurveyOpen(true)}
            />
          )}

          {state === "skipped" && (
            <StatePanel
              emphasis="primary"
              heading="No survey yet"
              body={
                daysSince !== null
                  ? `You skipped the survey ${friendlyTime(daysSince)} ago — totally fine. LyraOS's using a generic starting point until you take it. Time estimates personalize either way as you log sessions; the survey just gives LyraOS a head start.`
                  : "LyraOS's using a generic starting point until you take the survey. Time estimates personalize either way as you log sessions; the survey just gives LyraOS a head start."
              }
              buttonLabel="Take the survey"
              onClick={() => setSurveyOpen(true)}
            />
          )}

          {state === "calibrating" && (
            <StatePanel
              emphasis="secondary"
              heading="Settling in"
              body={
                sessionsToReveal === 1
                  ? "After one more session — start, work, finish — LyraOS will share a profile here that reflects how you actually work, not just how the survey read you. Time estimates are already personalizing in the background."
                  : `After about ${sessionsToReveal} more sessions — start, work, finish — LyraOS will share a profile here that reflects how you actually work, not just how the survey read you. Time estimates are already personalizing in the background.`
              }
              buttonLabel="Retake survey"
              onClick={() => setSurveyOpen(true)}
            />
          )}

          {state === "recent" && label && (
            <DynamicProfilePanel
              startingLabel={label}
              daysSince={daysSince ?? 0}
              ageEmphasis="recent"
              onRetake={() => setSurveyOpen(true)}
            />
          )}

          {state === "aged" && label && daysSince !== null && (
            <DynamicProfilePanel
              startingLabel={label}
              daysSince={daysSince}
              ageEmphasis="aged"
              onRetake={() => setSurveyOpen(true)}
            />
          )}
        </CardContent>
      </Card>

      {surveyOpen && (
        <ArchetypeSurvey
          onFinished={() => {
            setSurveyOpen(false);
            onChanged();
          }}
        />
      )}
    </>
  );
}

// Dynamic-reveal panel for the recent/aged states (MANIFESTO Rule 17,
// 2026-04-27). Replaces the prior static "Profile: <label>" StatePanel
// with the top-3 posterior view + retake-survey CTA below.
//
// `ageEmphasis="aged"` makes the retake button primary (>90 days = nudge
// toward refresh); "recent" keeps it secondary (<90 days = just an
// option). The dynamic posterior is the same in both cases — only the
// retake-CTA prominence + caption emphasis differ.
function DynamicProfilePanel({
  startingLabel,
  daysSince,
  ageEmphasis,
  onRetake,
}: {
  startingLabel: string;
  daysSince: number;
  ageEmphasis: "recent" | "aged";
  onRetake: () => void;
}) {
  const proximityQ = useQuery({
    queryKey: ["proximity", 14],
    queryFn: () => getArchetypeProximity(14),
    staleTime: 60_000,
  });
  const trendQ = useQuery({
    queryKey: ["proximity-trend", 14, 14],
    queryFn: () => getArchetypeProximityTrend(14, 14),
    staleTime: 60_000,
  });

  const isLoading = proximityQ.isLoading;
  const prox = proximityQ.data;
  const sparseRecent = prox && prox.n_tasks < 3;
  const top = prox?.proximity[0];

  const retakeBody =
    ageEmphasis === "aged"
      ? `It's been ${friendlyTime(daysSince)} since your last survey. ` +
        "Sleep rhythm, focus, the way you approach work — these things " +
        "shift. Take the survey again whenever you feel like the old " +
        "read no longer fits."
      : "You can retake the survey anytime — the dynamic pattern above " +
        "updates from your behavior either way, but a fresh survey " +
        "re-anchors the starting point.";

  const buttonVariant =
    ageEmphasis === "aged" ? "default" : ("outline" as const);

  return (
    <div className="flex flex-col gap-4 rounded-sm border border-hairline bg-void/30 px-4 py-3">
      <div>
        <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-dust-deep">
          Your last 14 days look most like…
        </div>
        {isLoading && (
          <div className="h-16 animate-pulse rounded-sm bg-void/40" />
        )}
        {!isLoading && sparseRecent && (
          <p className="text-sm leading-relaxed text-dust">
            LyraOS needs a few more recent sessions to show your current
            pattern. Your starting point was{" "}
            <span className="text-parchment">{startingLabel}</span>.
          </p>
        )}
        {!isLoading && !sparseRecent && prox && top && (
          <ArchetypeProximityRows top3={prox.proximity.slice(0, 3)} trend={trendQ.data} />
        )}
      </div>
      {!isLoading && !sparseRecent && top && trendQ.data && (
        <ArchetypeTrendCaption top={top} trend={trendQ.data} />
      )}
      {!isLoading && !sparseRecent && top && (
        <ArchetypeSaturationNote top={top} />
      )}
      <p className="text-xs leading-relaxed text-dust">
        Started as <span className="text-parchment">{startingLabel}</span>{" "}
        {friendlyTime(daysSince)} ago. {retakeBody}
      </p>
      <div className="flex justify-end">
        <Button
          type="button"
          size="sm"
          variant={buttonVariant}
          onClick={onRetake}
        >
          Retake survey
        </Button>
      </div>
    </div>
  );
}

function StatePanel({
  emphasis,
  heading,
  body,
  buttonLabel,
  onClick,
}: {
  emphasis: "primary" | "secondary";
  heading: string;
  body: string;
  buttonLabel: string;
  onClick: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex-1">
        <p className="text-sm font-medium text-parchment">{heading}</p>
        <p className="mt-1 text-xs leading-relaxed text-dust">{body}</p>
      </div>
      <div className="shrink-0">
        <Button
          variant={emphasis === "primary" ? "outline" : "ghost"}
          size="sm"
          onClick={onClick}
        >
          {buttonLabel}
        </Button>
      </div>
    </div>
  );
}

function classifyState(
  completed: boolean,
  latestAssignmentAt: string | null,
  executedSessionCount: number
): SectionState {
  if (latestAssignmentAt === null) return "no_assignment";
  if (!completed) return "skipped";
  // LYR-112: completed surveys with too few EXECUTED sessions stay in
  // calibrating — the label is hidden until LyraOS has watched the user
  // work enough to validate it against actual behavior.
  if (executedSessionCount < ARCHETYPE_REVEAL_MIN_SESSIONS) {
    return "calibrating";
  }
  const ageMs = Date.now() - new Date(latestAssignmentAt).getTime();
  return ageMs >= NINETY_DAYS_MS ? "aged" : "recent";
}

function friendlyTime(days: number): string {
  if (days < 1) return "less than a day";
  if (days === 1) return "1 day";
  if (days < 30) return `${days} days`;
  const months = Math.floor(days / 30);
  if (months === 1) return "about a month";
  if (months < 12) return `${months} months`;
  const years = Math.floor(days / 365);
  return years === 1 ? "about a year" : `${years} years`;
}

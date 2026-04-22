"use client";
/**
 * Archetype profile section — persistent Settings surface.
 *
 * Replaces the original retrofit banner (2026-04-22 operator feedback:
 * "allow button in settings to try later, allow retry for users who
 * already entered once after 3 months"). Always visible; copy and
 * button prominence vary by user state.
 *
 * States handled (in priority order):
 *
 *   1. NO ASSIGNMENT (fresh pre-launch user OR eligibility window)
 *      → "Take the 4-min survey to unlock personalized predictions"
 *      → Primary [Take survey]
 *
 *   2. SKIPPED (completed=False, defaulted to Diffuse Average)
 *      → "Using population-average predictions. Take the survey
 *         anytime to personalize."
 *      → Primary [Take survey]
 *
 *   3. RECENT COMPLETION (<90 days)
 *      → "Profile: <label> · assigned N days ago"
 *      → Secondary [Retake survey] (low prominence)
 *
 *   4. AGED COMPLETION (≥90 days — operator's 3-month retry rule)
 *      → "Profile: <label> · assigned N months ago. Your patterns may
 *         have shifted — retake to refresh."
 *      → Primary [Retake survey] (emphasized)
 *
 * Research note: re-takes write NEW ArchetypeAssignment rows
 * (submit_archetype_survey is additive). The original assignment
 * stays in history for longitudinal stability analysis (Gate 5).
 * User.archetype_id flips to the latest assignment's archetype_id,
 * which is what the Rule-13 blend reads.
 */
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArchetypeSurvey } from "@/components/archetype-survey";
import { ARCHETYPE_LABELS } from "@/lib/archetype";

const NINETY_DAYS_MS = 90 * 24 * 60 * 60 * 1000;

export interface ArchetypeProfileSectionProps {
  /** Current archetype_id from /me. Null when no assignment exists. */
  archetypeId: string | null;
  /** True only if the user has a completed=True ArchetypeAssignment. */
  completed: boolean;
  /** ISO timestamp of the latest assignment (completed OR skipped). */
  latestAssignmentAt: string | null;
  /** Called after survey submit / skip — parent refetches /me. */
  onChanged: () => void;
}

export function ArchetypeProfileSection({
  archetypeId,
  completed,
  latestAssignmentAt,
  onChanged,
}: ArchetypeProfileSectionProps) {
  const [surveyOpen, setSurveyOpen] = useState(false);

  const state = classifyState(completed, latestAssignmentAt);
  const daysSince = latestAssignmentAt
    ? Math.floor(
        (Date.now() - new Date(latestAssignmentAt).getTime()) /
          (24 * 60 * 60 * 1000)
      )
    : null;

  const label = archetypeId
    ? ARCHETYPE_LABELS[archetypeId] ?? archetypeId
    : null;

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Your archetype profile</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 p-4 pt-0">
          {state === "no_assignment" && (
            <StatePanel
              emphasis="primary"
              heading="No profile yet"
              body="Take the 4-minute calibration survey to unlock
                personalized predictions. Lyra will tune its time
                estimates to how you actually work instead of defaulting
                to population averages."
              buttonLabel="Take survey"
              onClick={() => setSurveyOpen(true)}
            />
          )}

          {state === "skipped" && (
            <StatePanel
              emphasis="primary"
              heading="Using population-average predictions"
              body={
                daysSince !== null
                  ? `You skipped the calibration survey ${friendlyTime(daysSince)} ago. Lyra is using the population-average prior (Diffuse Average) until you take it. No pressure — it's optional.`
                  : "You skipped the calibration survey. Lyra is using the population-average prior until you take it."
              }
              buttonLabel="Take survey"
              onClick={() => setSurveyOpen(true)}
            />
          )}

          {state === "recent" && label && daysSince !== null && (
            <StatePanel
              emphasis="secondary"
              heading={`Profile: ${label}`}
              body={`Assigned ${friendlyTime(daysSince)} ago. Lyra is
                blending this prior with your personal data as you
                accumulate sessions. You can retake the survey anytime.`}
              buttonLabel="Retake survey"
              onClick={() => setSurveyOpen(true)}
            />
          )}

          {state === "aged" && label && daysSince !== null && (
            <StatePanel
              emphasis="primary"
              heading={`Profile: ${label} · ${friendlyTime(daysSince)} ago`}
              body="It's been 3+ months since your last calibration.
                Your sleep rhythm, discipline patterns, or task
                approach may have shifted. Retake the survey to refresh
                Lyra's starting assumptions about you."
              buttonLabel="Retake survey"
              onClick={() => setSurveyOpen(true)}
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
  latestAssignmentAt: string | null
): "no_assignment" | "skipped" | "recent" | "aged" {
  if (latestAssignmentAt === null) return "no_assignment";
  if (!completed) return "skipped";
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

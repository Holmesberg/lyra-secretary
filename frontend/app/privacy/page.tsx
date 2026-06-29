const sections = [
  {
    title: "What Lyra Collects",
    body: [
      "Account data, such as your email address, Google account identifier, Google profile name when available, timezone, consent timestamps, onboarding state, and account settings.",
      "Planning and execution data, such as tasks, deadlines, task notes or descriptions you enter, categories, planned and executed times, timer sessions, pause and resume events, corrections, readiness ratings, completion percentages, reflection responses, and scope outcomes.",
      "Integration data, such as connected-provider state, imported calendar or Moodle deadline facts, external attendance or completion candidates, provider provenance, sync timestamps, and disconnect or sync-failure state.",
      "Product telemetry needed to make Lyra reliable, such as notification lifecycle events, exposure decisions, renders, acknowledgements, suppressions, email engagement events, feedback rows, error context that you choose to include, and security or governance audit records.",
    ],
  },
  {
    title: "How Lyra Uses Data",
    body: [
      "Lyra uses your data to run the product: create and schedule tasks, operate timers, recover from interruptions, sync connected integrations, display reminders and insights, export or delete your account, debug reliability issues, and measure whether the product is safe to expand to more users.",
      "Lyra may analyze product traces to improve planning, recovery, and measurement quality. These analyses are treated as bounded product hypotheses, not diagnoses, identity labels, professional advice, or claims about your motivation, discipline, focus, agency, or competence.",
      "Lyra does not sell your data and does not share it for advertising.",
    ],
  },
  {
    title: "Integrations And Service Providers",
    body: [
      "Lyra relies on service providers such as Cloudflare, Supabase, Google sign-in, Google Calendar when connected, Moodle when connected, Notion sync plumbing where enabled, Resend for email, and OpenClaw or Telegram for operator notification delivery when configured.",
      "Google Calendar refresh tokens, Moodle tokens, and private Moodle calendar URLs are treated as credential-class secrets. Lyra stores them so server-side sync can work, redacts them from exports, and encrypts credential fields where the current runtime supports it.",
      "Imported provider facts are treated as provider evidence or candidates unless the product explicitly asks you to confirm them.",
    ],
  },
  {
    title: "Operator And Admin Access",
    body: [
      "Lyra is currently pre-alpha software operated as a small trusted-user system. Authorized operators may access internal dashboards, admin tools, feedback queues, logs, and database-backed diagnostics to keep the service running, investigate bugs, verify data-sovereignty behavior, and decide whether the cohort is ready to expand.",
      "The main operator cockpit is designed to be content-minimized: it avoids raw task titles, raw emails, provider tokens, and raw provider URLs by default. Some older or narrower admin surfaces can expose raw account emails, user IDs, feedback text, page URLs, user agents, error context, and operational timestamps.",
      "Normal user-notification mirrors to the operator channel are redacted to metadata where possible. User-submitted feedback and operator-owned system alerts may be delivered as full text to operator email, OpenClaw, or Telegram so they can be triaged.",
    ],
  },
  {
    title: "AI, Insights, And Future Features",
    body: [
      "Current user-facing insights are intended to be deterministic and evidence-bounded. Optional hosted model paths or JARVIS-style tools may be used for operator-only debugging or enrichment workflows when configured.",
      "AI synthesis, behavior-transition equations, adaptive scheduling authority, new provider adapters, and new insight types are not automatically authorized by this policy. If Lyra ships those features later, the policy and consent surface must be updated before they become user-facing runtime behavior.",
      "Future AI or equation-based features must remain downstream of explicit evidence, uncertainty, privacy boundaries, and user-facing explanation. They must not create hidden identity labels or stronger claims than the underlying data supports.",
    ],
  },
  {
    title: "Export, Deletion, And Retention",
    body: [
      "You can export a secret-redacted JSON copy of your account data from Settings. Provider credentials, tokens, and private provider URLs are not included in raw form.",
      "When deleting your account, Lyra may offer two paths: hard deletion of user-owned product rows, or deletion of your account with anonymized retention of task and stopwatch-session timing rows for product-quality research. The retention path removes direct account identity and task text fields, but behavioral traces can still be sensitive and are not promised to be anonymous under every possible future linkage scenario.",
      "Security, abuse-prevention, and governance audit records may be retained separately from behavioral export/delete flows. Runtime cache and queue state is purged as part of the account deletion process where technically available.",
    ],
  },
  {
    title: "Surveys And External Research Forms",
    body: [
      "Lyra may also use separate voluntary surveys, including Google Forms linked to Google Sheets, to validate whether the problem is real and whether the product is useful. Those survey responses are outside the in-app Lyra runtime and are stored by the survey provider.",
      "Survey answers may include free text and optional contact information if you provide it. Do not include sensitive personal information in survey responses unless you are comfortable with it being reviewed for product research.",
    ],
  },
  {
    title: "Security Limits",
    body: [
      "Lyra uses authentication, operator-only route gates, credential redaction, credential encryption where implemented, audit logs, and data-minimizing dashboards to reduce risk.",
      "Lyra is not end-to-end encrypted. Authorized operators, infrastructure providers, and systems with database or runtime access may be able to access stored data as needed to operate and secure the service.",
      "No internet service can guarantee perfect security. Lyra should not be used for safety-critical, medical, legal, financial, or legally binding scheduling.",
    ],
  },
  {
    title: "Children, Changes, And Contact",
    body: [
      "Lyra is not intended for children under 13.",
      "This policy may change as Lyra moves from pre-alpha toward a broader release. Material changes should be reflected here before the related behavior is exposed to users.",
      "For privacy requests, use the in-app feedback link or the support/contact channel provided by the operator.",
    ],
  },
];

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl p-8 text-parchment">
      <div className="space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight">Privacy Policy</h1>
        <p className="text-sm text-dust">Last updated: June 24, 2026.</p>
        <p className="text-dust">
          LyraOS is pre-alpha personal planning and execution-tracking software.
          This policy describes current runtime behavior and the boundaries for
          future features.
        </p>
      </div>

      <div className="mt-8 space-y-8">
        {sections.map((section) => (
          <section key={section.title} className="space-y-3">
            <h2 className="text-xl font-semibold tracking-tight">
              {section.title}
            </h2>
            <div className="space-y-3 text-sm leading-6 text-dust">
              {section.body.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}

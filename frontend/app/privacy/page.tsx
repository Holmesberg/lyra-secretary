export default function PrivacyPage() {
  return (
    <main className="max-w-2xl mx-auto p-8 prose prose-invert">
      <h1>Privacy Policy</h1>
      <p className="text-muted-foreground">Last updated: May 15, 2026.</p>
      <p>
        LyraOS is pre-alpha software. It stores the tasks you create, planned
        and executed timing, timer sessions, pauses, deadlines, readiness and
        reflection responses where used, integration metadata, feedback, and
        account/export/deletion records.
      </p>
      <p>
        LyraOS does not sell your data or share it for advertising. The service
        relies on infrastructure and integration providers such as Cloudflare,
        Supabase, Google sign-in, Google Calendar when connected, Moodle when
        connected, and Notion sync plumbing where enabled. Optional hosted model
        paths may be used for operator or enrichment workflows when configured.
      </p>
      <p>
        Product insights are treated as bounded hypotheses from your traces, not
        psychological diagnoses or identity labels. You can export or delete
        your account data from Settings.
      </p>
    </main>
  );
}

"use client";
import { useEffect, useState } from "react";
import { signOut, useSession } from "next-auth/react";
import { format } from "date-fns";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";

type DataSummary = {
  total_tasks: number;
  executed_count: number;
  skipped_count: number;
  planned_count: number;
  session_count: number;
  reflection_count: number;
  notion_enabled: boolean;
};

export default function SettingsPage() {
  const { data: session } = useSession();
  const userEmail = session?.user?.email ?? "";

  // --- Export ---
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  async function handleExport() {
    setExporting(true);
    setExportError(null);
    try {
      const data = await api("/v1/users/me/export");
      const json = JSON.stringify(data, null, 2);
      const blob = new Blob([json], { type: "application/json;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `lyra-export-${format(new Date(), "yyyy-MM-dd")}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      setExportError(e.message || "Export failed");
    } finally {
      setExporting(false);
    }
  }

  // --- Delete (two-stage) ---
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [stage, setStage] = useState<1 | 2 | 3>(1);
  const [summary, setSummary] = useState<DataSummary | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [retainForResearch, setRetainForResearch] = useState(true);
  const [confirmEmail, setConfirmEmail] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Fetch data summary when modal opens
  useEffect(() => {
    if (deleteOpen) {
      api<DataSummary>("/v1/users/me/data-summary")
        .then(setSummary)
        .catch(() => setSummary(null));
    }
  }, [deleteOpen]);

  function openDeleteModal() {
    setDeleteOpen(true);
    setStage(1);
    setAcknowledged(false);
    setRetainForResearch(true);
    setConfirmEmail("");
    setDeleteError(null);
    setDeleting(false);
  }

  function closeDeleteModal() {
    if (!deleting) setDeleteOpen(false);
  }

  async function handleDelete() {
    setDeleting(true);
    setDeleteError(null);
    setStage(3);
    try {
      await api("/v1/users/me", {
        method: "DELETE",
        body: JSON.stringify({
          confirm_email: confirmEmail,
          retain_for_research: retainForResearch,
        }),
      });
      signOut({ callbackUrl: "/" });
    } catch (e: any) {
      setDeleteError(e.message || "Delete failed");
      setStage(2);
      setDeleting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      {/* --- Export card --- */}
      <Card>
        <CardHeader>
          <CardTitle>Export your data</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="text-sm text-white/60">
            Download every task, session, and reflection tied to your account as
            a single JSON file.
          </p>
          <Button
            variant="outline"
            onClick={handleExport}
            disabled={exporting}
          >
            {exporting ? "Exporting\u2026" : "Export JSON"}
          </Button>
        </CardContent>
        {exportError && (
          <p className="px-6 pb-4 text-sm text-red-400">{exportError}</p>
        )}
      </Card>

      {/* --- Delete account card --- */}
      <Card>
        <CardHeader>
          <CardTitle className="text-red-300">Delete account</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="text-sm text-white/60">
            Permanently delete your account and all associated data. Export your
            data first if you want to keep a record.
          </p>
          <Button variant="destructive" onClick={openDeleteModal}>
            Delete account
          </Button>
        </CardContent>
      </Card>

      {/* --- Delete modal (three stages) --- */}
      <Dialog open={deleteOpen} onOpenChange={(o) => { if (!o) closeDeleteModal(); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-red-400">
              Permanently delete your account
            </DialogTitle>
          </DialogHeader>

          {/* ===== STAGE 1: Comprehension ===== */}
          {stage === 1 && (
            <>
              <DialogDescription className="sr-only">
                Review what will be deleted before proceeding.
              </DialogDescription>

              <div className="space-y-4 text-sm">
                <p className="text-white/80">
                  This action will delete all data tied to your account:
                </p>

                {summary ? (
                  <ul className="list-disc pl-5 space-y-1 text-white/60">
                    <li>
                      {summary.total_tasks} task{summary.total_tasks !== 1 && "s"}
                      {summary.total_tasks > 0 && (
                        <span className="text-white/40">
                          {" "}({summary.executed_count} executed, {summary.skipped_count} skipped, {summary.planned_count} planned)
                        </span>
                      )}
                    </li>
                    <li>
                      {summary.session_count} stopwatch session{summary.session_count !== 1 && "s"} and pause history
                    </li>
                    <li>
                      {summary.reflection_count} reflection{summary.reflection_count !== 1 && "s"} and readiness rating{summary.reflection_count !== 1 && "s"}
                    </li>
                    {summary.notion_enabled && (
                      <li>
                        All Notion sync state
                        <span className="text-white/40"> (Notion pages will not be deleted from your workspace)</span>
                      </li>
                    )}
                    <li>Account login and preferences</li>
                    <li>Backup snapshots from the last 30 days will be purged within 24 hours</li>
                  </ul>
                ) : (
                  <p className="text-white/40 italic">Loading data summary...</p>
                )}

                {/* Warning block */}
                <div className="rounded border border-red-500/30 bg-red-500/10 px-3 py-2">
                  <p className="text-red-300 text-sm">
                    This cannot be undone. Lyra does not retain copies of deleted
                    accounts. Export your data first if you want to keep a record.
                  </p>
                </div>

                {/* Export quick action */}
                <button
                  type="button"
                  onClick={handleExport}
                  disabled={exporting}
                  className="text-sm text-blue-400 hover:text-blue-300 underline underline-offset-2"
                >
                  {exporting ? "Exporting\u2026" : "Export data first \u2192"}
                </button>

                {/* Research retention section */}
                <div className="rounded border border-white/10 bg-white/5 px-3 py-2 space-y-2">
                  <p className="text-xs font-medium uppercase tracking-wide text-white/60">
                    Help us improve Lyra
                  </p>
                  <label className="flex items-start gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={retainForResearch}
                      onChange={(e) => setRetainForResearch(e.target.checked)}
                      className="mt-0.5 h-4 w-4 rounded border-white/20 bg-transparent accent-blue-500"
                    />
                    <span className="text-sm text-white/80 leading-tight">
                      Allow Lyra to retain my anonymized behavioral data to
                      understand how people leave the system and improve the product
                    </span>
                  </label>
                  <p className="text-xs text-white/40 leading-relaxed">
                    Without data from people who stop using Lyra, we can&apos;t
                    understand what makes the system fail for them. Retained data
                    has no identifying information and cannot be linked back to
                    you. It is used only to improve Lyra, not for academic
                    publication. Uncheck this box if you want all data
                    permanently purged.
                  </p>
                </div>

                {/* Required acknowledgment */}
                <label className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={acknowledged}
                    onChange={(e) => setAcknowledged(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-white/20 bg-transparent accent-red-500"
                  />
                  <span className="text-sm text-white/80 leading-tight">
                    I understand this action is permanent and unrecoverable
                  </span>
                </label>
              </div>

              <DialogFooter>
                <Button variant="ghost" onClick={closeDeleteModal}>
                  Cancel
                </Button>
                <Button
                  onClick={() => setStage(2)}
                  disabled={!acknowledged}
                >
                  Continue
                </Button>
              </DialogFooter>
            </>
          )}

          {/* ===== STAGE 2: Identity verification ===== */}
          {stage === 2 && (
            <>
              <DialogDescription className="sr-only">
                Verify your identity to confirm account deletion.
              </DialogDescription>

              <div className="space-y-4 text-sm">
                <p className="text-white/80">
                  To confirm, type your email address:
                </p>
                <p className="text-white/40 text-xs font-mono">
                  {userEmail
                    ? userEmail.replace(/^(.{2})(.*)(@.*)$/, (_, a, b, c) => a + "*".repeat(b.length) + c)
                    : ""}
                </p>
                <Input
                  placeholder="your@email.com"
                  value={confirmEmail}
                  onChange={(e) => setConfirmEmail(e.target.value)}
                  disabled={deleting}
                  autoFocus
                />
                {deleteError && (
                  <p className="text-sm text-red-400">{deleteError}</p>
                )}
              </div>

              <DialogFooter>
                <Button
                  variant="ghost"
                  onClick={() => { setStage(1); setDeleteError(null); }}
                  disabled={deleting}
                >
                  Back
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={deleting || confirmEmail !== userEmail}
                >
                  Permanently delete account
                </Button>
              </DialogFooter>
            </>
          )}

          {/* ===== STAGE 3: Processing ===== */}
          {stage === 3 && (
            <>
              <DialogDescription className="sr-only">
                Deleting your account.
              </DialogDescription>

              <div className="flex flex-col items-center gap-3 py-6">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                <p className="text-sm text-white/60">
                  Deleting your account...
                </p>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

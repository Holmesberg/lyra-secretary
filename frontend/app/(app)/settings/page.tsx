"use client";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Export your data</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="text-sm text-white/60">
            Download every task, session, and reflection tied to your account as
            a single JSON file.
          </p>
          <Button variant="outline" disabled title="Wired in Phase 7">
            Export JSON
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-red-300">Delete account</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="text-sm text-white/60">
            Hard delete. Your user row, tasks, sessions, and reflections are
            removed irreversibly. There is no export triggered on delete —
            export first if you need a copy.
          </p>
          <Button variant="destructive" disabled title="Wired in Phase 7">
            Delete account
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

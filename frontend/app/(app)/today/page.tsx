"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Plus } from "lucide-react";
import {
  queryTasks,
  getStopwatchStatus,
  startStopwatch,
  stopStopwatch,
  markAbandoned,
  type TaskRow as TaskRowType,
  type StopResponse,
} from "@/lib/tasks";
import { Button } from "@/components/ui/button";
import { TaskRow } from "@/components/task-row";
import { ActiveTimerBanner } from "@/components/active-timer-banner";
import { ReadinessModal } from "@/components/readiness-modal";
import { ReflectionModal } from "@/components/reflection-modal";
import { NewTaskModal } from "@/components/new-task-modal";

function todayLocal() {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export default function TodayPage() {
  const qc = useQueryClient();
  const date = todayLocal();

  const tasksQ = useQuery({
    queryKey: ["tasks", date],
    queryFn: () => queryTasks(date),
  });
  const statusQ = useQuery({
    queryKey: ["stopwatch-status"],
    queryFn: getStopwatchStatus,
  });

  const [newTaskOpen, setNewTaskOpen] = useState(false);
  const [readinessFor, setReadinessFor] = useState<TaskRowType | null>(null);
  const [reflectionOpen, setReflectionOpen] = useState(false);
  const [earlyStop, setEarlyStop] = useState<{
    elapsed: number;
    planned: number;
    message: string;
  } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["tasks", date] });
    qc.invalidateQueries({ queryKey: ["stopwatch-status"] });
  };

  const status = statusQ.data;
  const activeTaskId = status?.active ? status.task_id : undefined;
  const timerBusy = !!status?.active;

  async function handleStart(task: TaskRowType, readiness: number) {
    setErrorMsg(null);
    try {
      await startStopwatch(task.task_id, readiness);
      setReadinessFor(null);
      refresh();
    } catch (e: any) {
      setErrorMsg(e?.message ?? "Failed to start timer");
    }
  }

  async function handleStop(
    reflection: number,
    opts: { confirmed?: boolean } = {}
  ) {
    setErrorMsg(null);
    try {
      const res: StopResponse = await stopStopwatch(reflection, opts);
      if (res.requires_confirmation) {
        setEarlyStop({
          elapsed: res.duration_minutes,
          planned: res.planned_duration_minutes,
          message: res.confirmation_message ?? "Early stop",
        });
        return; // keep modal open, now in early-stop mode
      }
      setReflectionOpen(false);
      setEarlyStop(null);
      refresh();
    } catch (e: any) {
      setErrorMsg(e?.message ?? "Failed to stop timer");
    }
  }

  async function handleSkip(task: TaskRowType) {
    setErrorMsg(null);
    try {
      await markAbandoned(task.task_id, "user_skipped from Today view");
      refresh();
    } catch (e: any) {
      setErrorMsg(e?.message ?? "Failed to skip task");
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Today</h1>
          <p className="text-xs text-white/50">
            {format(new Date(), "EEEE, MMMM d")}
          </p>
        </div>
        <Button onClick={() => setNewTaskOpen(true)} disabled={timerBusy && false}>
          <Plus className="mr-1 h-4 w-4" />
          New task
        </Button>
      </div>

      {status && <ActiveTimerBanner status={status} />}

      {errorMsg && (
        <div className="mb-4 rounded border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-200">
          {errorMsg}
        </div>
      )}

      {tasksQ.isLoading && (
        <div className="text-sm text-white/50">Loading today's tasks…</div>
      )}

      {tasksQ.data && tasksQ.data.length === 0 && (
        <div className="rounded-lg border border-dashed border-white/10 p-10 text-center text-sm text-white/50">
          Nothing scheduled yet. Create your first task.
        </div>
      )}

      {tasksQ.data && tasksQ.data.length > 0 && (
        <div className="flex flex-col gap-2">
          {tasksQ.data.map((t) => (
            <TaskRow
              key={t.task_id}
              task={t}
              disableStart={timerBusy && t.task_id !== activeTaskId}
              onStart={(task) => setReadinessFor(task)}
              onStop={() => setReflectionOpen(true)}
              onSkip={handleSkip}
            />
          ))}
        </div>
      )}

      {readinessFor && (
        <ReadinessModal
          open={!!readinessFor}
          taskTitle={readinessFor.title}
          onCancel={() => setReadinessFor(null)}
          onConfirm={(r) => handleStart(readinessFor, r)}
        />
      )}

      <ReflectionModal
        open={reflectionOpen}
        taskTitle={status?.task_title ?? ""}
        earlyStop={earlyStop}
        onCancel={() => {
          setReflectionOpen(false);
          setEarlyStop(null);
        }}
        onConfirm={(r, opts) => handleStop(r, { confirmed: opts?.confirmed })}
      />

      <NewTaskModal
        open={newTaskOpen}
        onClose={() => setNewTaskOpen(false)}
        onCreated={refresh}
      />
    </div>
  );
}

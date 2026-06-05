"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ackPendingNotifications,
  getPendingNotifications,
} from "@/lib/tasks";
import { Toast } from "@/components/toast";

interface ToastEntry {
  id: string;
  dedupeKey: string;
  message: string;
  lifespan: "auto" | "pin";
  detailHref?: string;
  priority: number;
}

const MAX_VISIBLE_TOASTS = 3;
const surfacedNotificationIds = new Set<string>();
const surfacedToastKeys = new Set<string>();

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function formatMinutes(value: unknown): string {
  const minutes = Math.max(0, Math.round(asNumber(value) ?? 0));
  if (minutes >= 60) {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return `${h}h${m ? ` ${m}m` : ""}`;
  }
  return `${minutes}m`;
}

function notificationId(notification: Record<string, unknown>): string {
  return (
    asString(notification.notification_id) ??
    asString(notification.firing_id) ??
    asString(notification.session_id) ??
    asString(notification.task_id) ??
    `notification-${JSON.stringify(notification)}`
  );
}

function toUserToast(notification: Record<string, unknown>): Omit<ToastEntry, "id"> | null {
  const type = asString(notification.type);
  if (type === "timer_overflow") {
    const elapsed = formatMinutes(notification.elapsed_minutes);
    const planned = formatMinutes(notification.planned_minutes);
    return {
      dedupeKey: "timer_overflow",
      message: `Task is past its planned window (${elapsed} active; planned ${planned}). Open it to stop or correct.`,
      lifespan: "pin",
      detailHref: "/pulse",
      priority: 0,
    };
  }
  if (type === "reminder") {
    return {
      dedupeKey: "reminder",
      message: "A planned task is coming up. Open Lyra to check the next block.",
      lifespan: "auto",
      detailHref: "/pulse",
      priority: 3,
    };
  }
  if (type === "resume_prediction") {
    const title = asString(notification.task_title) ?? "this task";
    const taskId = asString(notification.task_id) ?? title;
    return {
      dedupeKey: `resume_prediction:${taskId}`,
      message: `You left ${title} paused ${formatMinutes(
        notification.paused_for_minutes
      )} ago. Pick it back up?`,
      lifespan: "pin",
      detailHref: "/pulse",
      priority: 1,
    };
  }
  if (type === "pause_prediction") {
    const taskId = asString(notification.task_id) ?? "current";
    return {
      dedupeKey: `pause_prediction:${taskId}`,
      message: "This task has been open for a while. Open it to pause or continue.",
      lifespan: "auto",
      detailHref: "/pulse",
      priority: 2,
    };
  }
  return null;
}

export function AppNotificationHost() {
  const [toasts, setToasts] = useState<ToastEntry[]>([]);
  const surfaced = useRef<Set<string>>(new Set());

  const notificationsQ = useQuery({
    queryKey: ["notifications-web-pending"],
    queryFn: getPendingNotifications,
    staleTime: 10_000,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
  });

  const notifications = useMemo(
    () => notificationsQ.data?.notifications ?? [],
    [notificationsQ.data?.notifications]
  );

  useEffect(() => {
    if (notifications.length === 0) return;
    const ackIds: string[] = [];
    const nextToasts: ToastEntry[] = [];
    for (const notification of notifications) {
      const id = notificationId(notification);
      ackIds.push(id);
      if (surfaced.current.has(id) || surfacedNotificationIds.has(id)) continue;
      surfaced.current.add(id);
      surfacedNotificationIds.add(id);
      const toast = toUserToast(notification);
      if (!toast) continue;
      if (surfacedToastKeys.has(toast.dedupeKey)) continue;
      surfacedToastKeys.add(toast.dedupeKey);
      nextToasts.push({ id, ...toast });
    }
    if (nextToasts.length > 0) {
      setToasts((prev) =>
        [...prev, ...nextToasts]
          .sort((a, b) => a.priority - b.priority)
          .slice(0, MAX_VISIBLE_TOASTS)
      );
    }
    ackPendingNotifications(ackIds).catch(() => {
      /* Non-blocking: if ack fails, the next poll may retry. */
    });
  }, [notifications]);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed right-4 top-4 z-[90] flex flex-col gap-3">
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          id={toast.id}
          message={toast.message}
          lifespan={toast.lifespan}
          detailHref={toast.detailHref}
          onDismiss={(id) =>
            setToasts((prev) => prev.filter((item) => item.id !== id))
          }
        />
      ))}
    </div>
  );
}

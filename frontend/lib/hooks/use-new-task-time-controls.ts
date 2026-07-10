"use client";

import { useCallback, useMemo, useState } from "react";
import {
  addMinutes,
  defaultStart,
  defaultStartForDate,
  diffMinutes,
  formatLocal,
  suggestAmPmSwap as getAmPmSwapSuggestion,
  suggestPushStartToFuture as getPushStartToFutureSuggestion,
} from "@/lib/task-time";

export interface UseNewTaskTimeControlsOptions {
  defaultDate?: string;
  now: Date;
  onEditScheduleChanged?: () => void;
}

export function useNewTaskTimeControls({
  defaultDate,
  now,
  onEditScheduleChanged,
}: UseNewTaskTimeControlsOptions) {
  const [start, setStart] = useState(() => defaultStart());
  const [end, setEnd] = useState(() => defaultStart());
  const [durHours, setDurHours] = useState(0);
  const [durMinutes, setDurMinutes] = useState(0);

  const totalMinutes = durHours * 60 + durMinutes;
  const endBeforeStart = diffMinutes(start, end) <= 0;
  const suggestAmPmSwap = endBeforeStart
    ? getAmPmSwapSuggestion(start, end)
    : null;
  const suggestPushStartToFuture = getPushStartToFutureSuggestion(start, now);

  const nextDefaultStart = useCallback(() => {
    return defaultDate ? defaultStartForDate(defaultDate, now) : defaultStart(now);
  }, [defaultDate, now]);

  const resetTimeDefaults = useCallback(() => {
    const nextStart = nextDefaultStart();
    setStart(nextStart);
    setEnd(nextStart);
    setDurHours(0);
    setDurMinutes(0);
  }, [nextDefaultStart]);

  const loadTimeRange = useCallback((startDate: Date, endDate: Date) => {
    const dur = Math.max(
      0,
      Math.round((endDate.getTime() - startDate.getTime()) / 60_000),
    );
    setStart(formatLocal(startDate));
    setEnd(formatLocal(endDate));
    setDurHours(Math.floor(dur / 60));
    setDurMinutes(dur % 60);
  }, []);

  const handleStartChange = useCallback(
    (newStart: string) => {
      onEditScheduleChanged?.();
      const dur = durHours * 60 + durMinutes;
      setStart(newStart);
      setEnd(addMinutes(newStart, dur));
    },
    [durHours, durMinutes, onEditScheduleChanged],
  );

  const handleEndChange = useCallback(
    (newEnd: string) => {
      onEditScheduleChanged?.();
      setEnd(newEnd);
      const mins = diffMinutes(start, newEnd);
      if (mins > 0) {
        setDurHours(Math.floor(mins / 60));
        setDurMinutes(mins % 60);
      } else {
        setDurHours(0);
        setDurMinutes(0);
      }
    },
    [onEditScheduleChanged, start],
  );

  const handleDurHoursChange = useCallback(
    (h: number) => {
      onEditScheduleChanged?.();
      const clamped = Math.max(0, h);
      setDurHours(clamped);
      setEnd(addMinutes(start, clamped * 60 + durMinutes));
    },
    [durMinutes, onEditScheduleChanged, start],
  );

  const handleDurMinutesChange = useCallback(
    (m: number) => {
      onEditScheduleChanged?.();
      const clamped = Math.max(0, m);
      setDurMinutes(clamped);
      setEnd(addMinutes(start, durHours * 60 + clamped));
    },
    [durHours, onEditScheduleChanged, start],
  );

  const applyDurationMinutes = useCallback(
    (minutes: number) => {
      onEditScheduleChanged?.();
      const clamped = Math.max(0, minutes);
      setDurHours(Math.floor(clamped / 60));
      setDurMinutes(clamped % 60);
      setEnd(addMinutes(start, clamped));
    },
    [onEditScheduleChanged, start],
  );

  const applyAmPmSwap = useCallback(() => {
    if (!suggestAmPmSwap) return;
    handleEndChange(suggestAmPmSwap);
  }, [handleEndChange, suggestAmPmSwap]);

  const applyPushStartToFuture = useCallback(() => {
    if (!suggestPushStartToFuture) return;
    handleStartChange(suggestPushStartToFuture);
  }, [handleStartChange, suggestPushStartToFuture]);

  return useMemo(
    () => ({
      start,
      end,
      durHours,
      durMinutes,
      totalMinutes,
      endBeforeStart,
      suggestAmPmSwap,
      suggestPushStartToFuture,
      resetTimeDefaults,
      loadTimeRange,
      handleStartChange,
      handleEndChange,
      handleDurHoursChange,
      handleDurMinutesChange,
      applyDurationMinutes,
      applyAmPmSwap,
      applyPushStartToFuture,
    }),
    [
      applyAmPmSwap,
      applyDurationMinutes,
      applyPushStartToFuture,
      durHours,
      durMinutes,
      end,
      endBeforeStart,
      handleDurHoursChange,
      handleDurMinutesChange,
      handleEndChange,
      handleStartChange,
      loadTimeRange,
      resetTimeDefaults,
      start,
      suggestAmPmSwap,
      suggestPushStartToFuture,
      totalMinutes,
    ],
  );
}

import type { BrainDumpBindingSuggestion } from "@/lib/brain-dump";

export type BrainDumpBindingChoice = "yes" | "no";

export function pad2(n: number): string {
  return n.toString().padStart(2, "0");
}

export function localIsoNow(): string {
  const d = new Date();
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(
    d.getDate(),
  )}T${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

export function bindingKey(b: BrainDumpBindingSuggestion): string {
  return (
    b.binding_id ||
    `${b.task_item_id}:${b.target_kind}:${b.deadline_id ?? b.deadline_item_id}`
  );
}

export function initialBindingChoices(
  nextBindings: BrainDumpBindingSuggestion[],
): Record<string, BrainDumpBindingChoice> {
  const choices: Record<string, BrainDumpBindingChoice> = {};
  const acceptedTasks = new Set<string>();

  for (const b of nextBindings) {
    if (b.tier === "tier1_auto" && !acceptedTasks.has(b.task_item_id)) {
      choices[bindingKey(b)] = "yes";
      acceptedTasks.add(b.task_item_id);
    }
  }

  for (const b of nextBindings) {
    const key = bindingKey(b);
    if (acceptedTasks.has(b.task_item_id) && choices[key] !== "yes") {
      choices[key] = "no";
    }
  }

  return choices;
}

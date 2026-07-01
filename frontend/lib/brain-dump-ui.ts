import type {
  BrainDumpBindingSuggestion,
  BrainDumpCommitBinding,
  BrainDumpCommitItem,
  BrainDumpParsedItem,
} from "@/lib/brain-dump";

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

export function buildBrainDumpCommitItems(
  items: BrainDumpParsedItem[],
): BrainDumpCommitItem[] {
  return items.map((item) => ({
    item_id: item.item_id,
    kind: item.kind,
    title: item.title,
    description: item.description,
    when_local: item.when_local,
    duration_minutes: item.duration_minutes,
    category: item.category,
    category_source: item.category_source,
    duration_source: item.duration_source,
    duration_confidence: item.duration_confidence,
    duration_basis: item.duration_basis,
  }));
}

export function buildBrainDumpCommitBindings(
  bindings: BrainDumpBindingSuggestion[],
  bindingChoices: Record<string, BrainDumpBindingChoice>,
): BrainDumpCommitBinding[] {
  return bindings
    .filter((binding) => bindingChoices[bindingKey(binding)] === "yes")
    .map((binding) => ({
      task_item_id: binding.task_item_id,
      deadline_item_id:
        binding.target_kind === "parsed_deadline"
          ? binding.deadline_item_id
          : null,
      deadline_id:
        binding.target_kind === "existing_deadline"
          ? binding.deadline_id
          : null,
      target_kind: binding.target_kind,
    }));
}

export function failureCopy(
  reason: string,
  options: { duplicateDeadlineCopy?: boolean } = {},
): string {
  switch (reason) {
    case "past_time":
      return "the time is already in the past";
    case "missing_when":
      return "no due date was parsed";
    case "deadline_terminal_state":
      return "the linked deadline is already finished";
    case "deadline_not_found":
      return "couldn't find the linked deadline";
    case "duplicate_deadline":
      return options.duplicateDeadlineCopy
        ? "already exists; linked tasks use the existing deadline"
        : "couldn't be saved";
    case "conflict_blocked":
      return "blocked by a hard conflict with an active session";
    case "validation":
      return "didn't pass scheduling rules";
    default:
      return "couldn't be saved";
  }
}

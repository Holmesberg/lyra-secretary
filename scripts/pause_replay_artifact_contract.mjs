export function assertAggregateOnly(value, pathParts = []) {
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertAggregateOnly(item, [...pathParts, String(index)]));
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    const currentPath = [...pathParts, key];
    if (/^(?:task|session|user|pause|exposure|render|decision)_ids?$/i.test(key)) {
      throw new Error(`aggregate output contains forbidden row identifier: ${currentPath.join(".")}`);
    }
    if (/^(?:title|description|email|notes?|raw_response|token|cookie)$/i.test(key)) {
      throw new Error(`aggregate output contains forbidden private field: ${currentPath.join(".")}`);
    }
    assertAggregateOnly(child, currentPath);
  }
}

function sensitiveValues(exported) {
  const values = new Set();
  const visit = (value, key = "") => {
    if (Array.isArray(value)) return value.forEach((item) => visit(item, key));
    if (value && typeof value === "object") {
      return Object.entries(value).forEach(([childKey, child]) => visit(child, childKey));
    }
    if (
      typeof value === "string"
      && value.length >= 8
      && /^(?:title|description|email|notes?|task_id|session_id|user_id)$/i.test(key)
    ) {
      values.add(value);
    }
  };
  visit(exported);
  return values;
}

export function assertNoPrivateValues(aggregate, exported) {
  const serialized = JSON.stringify(aggregate);
  for (const value of sensitiveValues(exported)) {
    if (serialized.includes(value)) {
      throw new Error("aggregate output repeats a private export value");
    }
  }
}

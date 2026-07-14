#!/usr/bin/env node
import assert from "node:assert/strict";

import {
  createRelayOperations,
  processPendingRaw,
  relayText,
  sanitizeRelayReason,
} from "./openclaw_operator_relay.mjs";

const queueKey = "notifications:pending:test";
const processingKey = `${queueKey}:processing`;
const deadLetterKey = `${queueKey}:dead_letter`;

function createFakeRedis(initial = {}) {
  const lists = new Map();
  for (const [key, values] of Object.entries(initial)) {
    lists.set(key, [...values]);
  }

  const list = (key) => {
    if (!lists.has(key)) {
      lists.set(key, []);
    }
    return lists.get(key);
  };

  const commandLog = [];

  async function redisCommand(args) {
    commandLog.push(args.map(String));
    const [command, ...rest] = args.map(String);
    if (command === "RPOPLPUSH" || command === "BRPOPLPUSH") {
      const [source, destination] = rest;
      const value = list(source).pop() ?? null;
      if (value !== null) {
        list(destination).unshift(value);
      }
      return value;
    }
    if (command === "LREM") {
      const [key, countRaw, value] = rest;
      const count = Number(countRaw);
      const values = list(key);
      let removed = 0;
      for (let i = 0; i < values.length && removed < count; i += 1) {
        if (values[i] === value) {
          values.splice(i, 1);
          removed += 1;
          i -= 1;
        }
      }
      return removed;
    }
    if (command === "LPUSH") {
      const [key, value] = rest;
      list(key).unshift(value);
      return list(key).length;
    }
    throw new Error(`unexpected fake redis command ${command}`);
  }

  return {
    redisCommand,
    commandLog,
    list,
  };
}

function createOps(fakeRedis, logs) {
  return createRelayOperations({
    redisCommand: fakeRedis.redisCommand,
    queueKey,
    processingKey,
    deadLetterKey,
    pollTimeoutSeconds: 0,
    log: (line) => logs.push(line),
    now: () => new Date("2026-07-01T00:00:00.000Z"),
  });
}

async function testRestoreProcessingQueue() {
  const logs = [];
  const fakeRedis = createFakeRedis({
    [queueKey]: ["pending-a"],
    [processingKey]: ["processing-left", "processing-right"],
  });
  const ops = createOps(fakeRedis, logs);

  const restored = await ops.restoreProcessingQueue();

  assert.equal(restored, 2);
  assert.deepEqual(fakeRedis.list(processingKey), []);
  assert.deepEqual(fakeRedis.list(queueKey), [
    "processing-left",
    "processing-right",
    "pending-a",
  ]);
  assert.ok(logs.some((line) => line === "restored_processing count=2"));
}

async function testTakePendingMovesBeforeSendAndAckAfterSuccess() {
  const logs = [];
  const raw = JSON.stringify({
    type: "operator_alert",
    source: "test",
    message: "PRIVATE_PAYLOAD should send but not be logged",
  });
  const fakeRedis = createFakeRedis({ [queueKey]: [raw], [processingKey]: [] });
  const ops = createOps(fakeRedis, logs);

  const taken = await ops.takePending();
  assert.equal(taken, raw);
  assert.deepEqual(fakeRedis.list(queueKey), []);
  assert.deepEqual(fakeRedis.list(processingKey), [raw]);

  let sawProcessingBeforeSend = false;
  const result = await processPendingRaw(taken, { token: "TOKEN", chatIds: ["1"] }, ops, {
    sendTelegram: async (_token, _chatIds, text) => {
      sawProcessingBeforeSend = fakeRedis.list(processingKey).includes(raw);
      assert.equal(text, "PRIVATE_PAYLOAD should send but not be logged");
    },
    sleep: async () => {},
    log: (line) => logs.push(line),
  });

  assert.equal(result, "sent");
  assert.equal(sawProcessingBeforeSend, true);
  assert.deepEqual(fakeRedis.list(processingKey), []);
  assert.ok(logs.some((line) => line === "sent type=operator_alert source=test"));
  assert.equal(logs.some((line) => line.includes("PRIVATE_PAYLOAD")), false);
}

async function testSendFailureRequeuesWithoutSecretLogs() {
  const logs = [];
  const raw = JSON.stringify({
    type: "resume_prediction",
    source: "test",
    message: "PRIVATE_PAYLOAD",
  });
  const fakeRedis = createFakeRedis({ [queueKey]: [raw], [processingKey]: [] });
  const ops = createOps(fakeRedis, logs);

  const taken = await ops.takePending();
  const result = await processPendingRaw(taken, { token: "TOKEN", chatIds: ["1"] }, ops, {
    sendTelegram: async () => {
      throw new Error(
        "https://api.telegram.org/botSECRET/sendMessage?token=BAD&message=PRIVATE_PAYLOAD",
      );
    },
    sleep: async () => {},
    log: (line) => logs.push(line),
  });

  assert.equal(result, "requeued");
  assert.deepEqual(fakeRedis.list(processingKey), []);
  assert.deepEqual(fakeRedis.list(queueKey), [raw]);
  assert.ok(logs.some((line) => line.startsWith("requeued reason=send_failed:")));
  const joined = logs.join("\n");
  assert.equal(joined.includes("SECRET"), false);
  assert.equal(joined.includes("BAD"), false);
  assert.equal(joined.includes("PRIVATE_PAYLOAD"), false);
}

async function testMalformedJsonDeadLetters() {
  const logs = [];
  const raw = "{not-json";
  const fakeRedis = createFakeRedis({ [queueKey]: [raw], [processingKey]: [] });
  const ops = createOps(fakeRedis, logs);

  const taken = await ops.takePending();
  const result = await processPendingRaw(taken, { token: "TOKEN", chatIds: ["1"] }, ops, {
    sendTelegram: async () => {
      throw new Error("send should not run");
    },
    sleep: async () => {},
    log: (line) => logs.push(line),
  });

  assert.equal(result, "dead_lettered");
  assert.deepEqual(fakeRedis.list(processingKey), []);
  assert.equal(fakeRedis.list(deadLetterKey).length, 1);
  const entry = JSON.parse(fakeRedis.list(deadLetterKey)[0]);
  assert.equal(entry.raw, raw);
  assert.equal(entry.reason, "malformed_json:SyntaxError");
  assert.equal(entry.moved_at, "2026-07-01T00:00:00.000Z");
  assert.ok(logs.some((line) => line === "dead_lettered removed=1 reason=malformed_json:SyntaxError"));
}

function testRelayTextFallbackAndSanitizer() {
  assert.equal(
    relayText({ type: "operator_alert", source: "unit" }),
    "[warn] [openclaw.relay] LyraOS operator notification lacked message text. type=operator_alert source=unit",
  );
  const sanitized = sanitizeRelayReason(
    "https://api.telegram.org/botSECRET/sendMessage?token=BAD&message=PRIVATE_PAYLOAD",
  );
  assert.equal(sanitized.includes("SECRET"), false);
  assert.equal(sanitized.includes("BAD"), false);
  assert.equal(sanitized.includes("PRIVATE_PAYLOAD"), false);
}

await testRestoreProcessingQueue();
await testTakePendingMovesBeforeSendAndAckAfterSuccess();
await testSendFailureRequeuesWithoutSecretLogs();
await testMalformedJsonDeadLetters();
testRelayTextFallbackAndSanitizer();

console.log(
  JSON.stringify(
    {
      ok: true,
      checks: [
        "restore processing to pending",
        "pending moves to processing before send",
        "successful send acks after send",
        "send failure requeues without secret logs",
        "malformed JSON dead-letters",
        "relay text fallback and reason sanitizer",
      ],
    },
    null,
    2,
  ),
);

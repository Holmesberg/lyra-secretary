/*
 * LyraOS client shadow export, read-only.
 *
 * Usage:
 *   1. Open DevTools in the page or extension context that may contain data.
 *   2. Paste this exact file contents.
 *   3. Save the downloaded JSON or copy __LYRAOS_SHADOW_EXPORT_JSON__.
 *
 * Do not ask an LLM to rewrite this during an incident.
 * This script is intentionally read-only with respect to browser storage.
 */

(async () => {
  "use strict";

  const EXPORT_VERSION = "lyraos-client-shadow-readonly-v1";
  const startedAt = new Date().toISOString();

  function makeJsonReplacer() {
    const seen = new WeakSet();
    return (_key, value) => {
      if (typeof value === "bigint") {
        return { __type: "bigint", value: value.toString() };
      }
      if (typeof ArrayBuffer !== "undefined" && value instanceof ArrayBuffer) {
        return { __type: "ArrayBuffer", byteLength: value.byteLength };
      }
      if (typeof Blob !== "undefined" && value instanceof Blob) {
        return { __type: "Blob", size: value.size, type: value.type || null };
      }
      if (value && typeof value === "object") {
        if (seen.has(value)) {
          return { __type: "CircularReference" };
        }
        seen.add(value);
      }
      return value;
    };
  }

  function readWebStorage(area, label) {
    const result = {
      label,
      available: false,
      item_count: 0,
      items: {},
      error: null,
    };

    try {
      if (!area) {
        result.error = "storage area unavailable";
        return result;
      }
      result.available = true;
      result.item_count = area.length;
      for (let index = 0; index < area.length; index += 1) {
        const key = area.key(index);
        if (key === null) {
          continue;
        }
        result.items[key] = area.getItem(key);
      }
      return result;
    } catch (error) {
      result.error = String(error && error.message ? error.message : error);
      return result;
    }
  }

  function requestToPromise(request) {
    return new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("request failed"));
    });
  }

  function transactionDone(transaction) {
    return new Promise((resolve, reject) => {
      transaction.oncomplete = () => resolve();
      transaction.onabort = () => reject(transaction.error || new Error("transaction aborted"));
      transaction.onerror = () => reject(transaction.error || new Error("transaction failed"));
    });
  }

  async function readObjectStore(db, storeName) {
    const transaction = db.transaction(storeName, "readonly");
    const store = transaction.objectStore(storeName);
    const valuesPromise = requestToPromise(store.getAll());
    const keysPromise =
      typeof store.getAllKeys === "function"
        ? requestToPromise(store.getAllKeys())
        : Promise.resolve(null);

    const [keys, values] = await Promise.all([keysPromise, valuesPromise]);
    await transactionDone(transaction);

    return {
      store_name: storeName,
      key_path: store.keyPath || null,
      auto_increment: Boolean(store.autoIncrement),
      record_count: Array.isArray(values) ? values.length : null,
      keys,
      values,
    };
  }

  async function readIndexedDb() {
    const output = {
      available: false,
      database_list_supported: false,
      databases: [],
      error: null,
    };

    try {
      if (!globalThis.indexedDB) {
        output.error = "indexedDB unavailable";
        return output;
      }
      output.available = true;
      if (typeof globalThis.indexedDB.databases !== "function") {
        output.error = "indexedDB.databases() unsupported in this browser/context";
        return output;
      }
      output.database_list_supported = true;
      const dbInfos = await globalThis.indexedDB.databases();

      for (const info of dbInfos) {
        if (!info || !info.name) {
          continue;
        }

        const dbResult = {
          name: info.name,
          version: info.version || null,
          object_stores: [],
          error: null,
        };

        try {
          const openRequest = globalThis.indexedDB.open(info.name);
          const db = await requestToPromise(openRequest);
          try {
            const storeNames = Array.from(db.objectStoreNames || []);
            for (const storeName of storeNames) {
              try {
                dbResult.object_stores.push(await readObjectStore(db, storeName));
              } catch (storeError) {
                dbResult.object_stores.push({
                  store_name: storeName,
                  error: String(storeError && storeError.message ? storeError.message : storeError),
                });
              }
            }
          } finally {
            db.close();
          }
        } catch (dbError) {
          dbResult.error = String(dbError && dbError.message ? dbError.message : dbError);
        }

        output.databases.push(dbResult);
      }

      return output;
    } catch (error) {
      output.error = String(error && error.message ? error.message : error);
      return output;
    }
  }

  function readChromeStorageArea(area, label) {
    return new Promise((resolve) => {
      const result = {
        label,
        available: false,
        items: null,
        error: null,
      };

      try {
        if (!area || typeof area.get !== "function") {
          result.error = "chrome storage area unavailable in this context";
          resolve(result);
          return;
        }

        result.available = true;
        area.get(null, (items) => {
          const lastError =
            globalThis.chrome &&
            globalThis.chrome.runtime &&
            globalThis.chrome.runtime.lastError;
          if (lastError) {
            result.error = lastError.message || String(lastError);
          }
          result.items = items || {};
          resolve(result);
        });
      } catch (error) {
        result.error = String(error && error.message ? error.message : error);
        resolve(result);
      }
    });
  }

  async function readChromeStorage() {
    const storage =
      globalThis.chrome && globalThis.chrome.storage ? globalThis.chrome.storage : null;
    return {
      available: Boolean(storage),
      local: await readChromeStorageArea(storage && storage.local, "chrome.storage.local"),
      sync: await readChromeStorageArea(storage && storage.sync, "chrome.storage.sync"),
    };
  }

  function browserContextSummary() {
    const locationSummary =
      globalThis.location && globalThis.location.href
        ? {
            href: globalThis.location.href,
            origin: globalThis.location.origin || null,
            protocol: globalThis.location.protocol || null,
          }
        : null;

    return {
      user_agent:
        globalThis.navigator && globalThis.navigator.userAgent
          ? globalThis.navigator.userAgent
          : null,
      location: locationSummary,
      has_document: Boolean(globalThis.document),
      has_chrome_storage: Boolean(
        globalThis.chrome && globalThis.chrome.storage
      ),
    };
  }

  function saveExport(payload) {
    const json = JSON.stringify(payload, makeJsonReplacer(), 2);
    const fileName = `lyraos-client-shadow-export-${startedAt.replace(/[:.]/g, "-")}.json`;

    globalThis.__LYRAOS_SHADOW_EXPORT__ = payload;
    globalThis.__LYRAOS_SHADOW_EXPORT_JSON__ = json;

    if (typeof globalThis.copy === "function") {
      try {
        globalThis.copy(json);
        console.info("LyraOS shadow export JSON copied to clipboard by DevTools copy().");
      } catch (error) {
        console.warn("DevTools copy() failed; use __LYRAOS_SHADOW_EXPORT_JSON__.", error);
      }
    }

    if (globalThis.document && typeof Blob !== "undefined" && globalThis.URL) {
      const blob = new Blob([json], { type: "application/json" });
      const url = globalThis.URL.createObjectURL(blob);
      const anchor = globalThis.document.createElement("a");
      anchor.href = url;
      anchor.download = fileName;
      anchor.style.display = "none";
      globalThis.document.body.appendChild(anchor);
      anchor.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
      globalThis.URL.revokeObjectURL(url);
      console.info(`LyraOS shadow export download requested: ${fileName}`);
      return;
    }

    console.info("No document download context. Read __LYRAOS_SHADOW_EXPORT_JSON__.");
  }

  const payload = {
    export_version: EXPORT_VERSION,
    created_at: new Date().toISOString(),
    read_only: true,
    warning:
      "This file was generated by the canonical LyraOS read-only client shadow exporter.",
    context: browserContextSummary(),
    web_storage: {
      local_storage: readWebStorage(globalThis.localStorage, "localStorage"),
      session_storage: readWebStorage(globalThis.sessionStorage, "sessionStorage"),
    },
    indexed_db: await readIndexedDb(),
    chrome_storage: await readChromeStorage(),
  };

  saveExport(payload);
})();

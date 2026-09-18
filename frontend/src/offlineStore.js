const DB_NAME = "medikiosk-offline";
const DB_VERSION = 1;
const STORES = { mutations: "mutations", drafts: "drafts", files: "files" };

function openDb() {
  if (typeof indexedDB === "undefined") return Promise.resolve(null);
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORES.mutations)) {
        db.createObjectStore(STORES.mutations, { keyPath: "id", autoIncrement: true });
      }
      if (!db.objectStoreNames.contains(STORES.drafts)) {
        db.createObjectStore(STORES.drafts, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(STORES.files)) {
        db.createObjectStore(STORES.files, { keyPath: "id", autoIncrement: true });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function transaction(storeName, mode, operation) {
  const db = await openDb();
  if (!db) return operation(null);
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, mode);
    const store = tx.objectStore(storeName);
    let result;
    try {
      result = operation(store);
    } catch (error) {
      reject(error);
      return;
    }
    tx.oncomplete = () => resolve(result);
    tx.onerror = () => reject(tx.error);
  });
}

function localFallbackKey(store, id) {
  return `medikiosk-offline:${store}:${id}`;
}

export async function saveDraft(id, value) {
  const record = { id, value, updatedAt: new Date().toISOString() };
  if (typeof indexedDB === "undefined") {
    localStorage.setItem(localFallbackKey(STORES.drafts, id), JSON.stringify(record));
    return;
  }
  await transaction(STORES.drafts, "readwrite", (store) => store.put(record));
}

export async function getDraft(id) {
  if (typeof indexedDB === "undefined") {
    const raw = localStorage.getItem(localFallbackKey(STORES.drafts, id));
    return raw ? JSON.parse(raw).value : null;
  }
  const db = await openDb();
  if (!db) return null;
  return new Promise((resolve, reject) => {
    const request = db.transaction(STORES.drafts, "readonly").objectStore(STORES.drafts).get(id);
    request.onsuccess = () => resolve(request.result?.value || null);
    request.onerror = () => reject(request.error);
  });
}

export async function deleteDraft(id) {
  if (typeof indexedDB === "undefined") {
    localStorage.removeItem(localFallbackKey(STORES.drafts, id));
    return;
  }
  await transaction(STORES.drafts, "readwrite", (store) => store.delete(id));
}

export async function enqueueMutation(mutation) {
  const record = { ...mutation, queuedAt: new Date().toISOString() };
  if (typeof indexedDB === "undefined") {
    const existing = JSON.parse(localStorage.getItem(localFallbackKey(STORES.mutations, "all")) || "[]");
    existing.push({ ...record, id: Date.now() });
    localStorage.setItem(localFallbackKey(STORES.mutations, "all"), JSON.stringify(existing));
    return;
  }
  await transaction(STORES.mutations, "readwrite", (store) => store.add(record));
}

export async function listMutations() {
  if (typeof indexedDB === "undefined") {
    return JSON.parse(localStorage.getItem(localFallbackKey(STORES.mutations, "all")) || "[]");
  }
  const db = await openDb();
  if (!db) return [];
  return new Promise((resolve, reject) => {
    const request = db.transaction(STORES.mutations, "readonly").objectStore(STORES.mutations).getAll();
    request.onsuccess = () => resolve(request.result || []);
    request.onerror = () => reject(request.error);
  });
}

export async function removeMutation(id) {
  if (typeof indexedDB === "undefined") {
    const remaining = (await listMutations()).filter((item) => item.id !== id);
    localStorage.setItem(localFallbackKey(STORES.mutations, "all"), JSON.stringify(remaining));
    return;
  }
  await transaction(STORES.mutations, "readwrite", (store) => store.delete(id));
}

export async function pendingMutationCount() {
  const files = await listFiles();
  return (await listMutations()).length + files.length;
}

export async function enqueueFile(fileRecord) {
  if (typeof indexedDB === "undefined") return;
  await transaction(STORES.files, "readwrite", (store) => store.add({ ...fileRecord, queuedAt: new Date().toISOString() }));
}

export async function listFiles() {
  if (typeof indexedDB === "undefined") return [];
  const db = await openDb();
  if (!db) return [];
  return new Promise((resolve, reject) => {
    const request = db.transaction(STORES.files, "readonly").objectStore(STORES.files).getAll();
    request.onsuccess = () => resolve(request.result || []);
    request.onerror = () => reject(request.error);
  });
}

export async function removeFile(id) {
  if (typeof indexedDB === "undefined") return;
  await transaction(STORES.files, "readwrite", (store) => store.delete(id));
}

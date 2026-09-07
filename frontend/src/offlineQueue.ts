import type { FieldReportInput } from "./types";

type QueuedEvidence = { name: string; type: string; dataUrl: string };
export type QueuedReport = {
  id: string;
  payload: FieldReportInput;
  evidence?: QueuedEvidence;
  queuedAt: string;
};

const DB_NAME = "raahsetu-offline";
const STORE = "field-reports";

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: "id" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Offline storage unavailable"));
  });
}

export async function queueReport(item: QueuedReport): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(item);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error ?? new Error("Could not queue report"));
  });
  db.close();
}

export async function listQueuedReports(): Promise<QueuedReport[]> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const request = db.transaction(STORE, "readonly").objectStore(STORE).getAll();
    request.onsuccess = () => { db.close(); resolve(request.result as QueuedReport[]); };
    request.onerror = () => { db.close(); reject(request.error); };
  });
}

export async function removeQueuedReport(id: string): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error ?? new Error("Could not remove queued report"));
  });
  db.close();
}

export async function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("Could not store evidence"));
    reader.readAsDataURL(file);
  });
}

export function dataUrlToFile(dataUrl: string, name: string, type: string): File {
  const [meta, data] = dataUrl.split(",");
  const bytes = Uint8Array.from(atob(data), (char) => char.charCodeAt(0));
  return new File([bytes], name, { type: meta.match(/data:([^;]+)/)?.[1] || type });
}

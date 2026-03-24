export type StoredChatShort = {
  itemId: string;
  batchId: string;
  itemIndex: number;
  title: string;
  sourceLabel: string;
  sourceUrl: string | null;
  status: string;
  outputUrl: string | null;
  previewUrl: string;
  thumbnailUrl: string | null;
  subtitleStyleLabel: string | null;
  subtitleAnimation: string | null;
  subtitleFontName: string | null;
  gameplayAssetPath: string | null;
  estimatedSeconds: number | null;
  narrationText: string | null;
  createdAt: string;
};

export type StoredChatBatch = {
  chatId: string;
  batchId: string;
  status: string;
  sourceLabel: string;
  sourceUrl: string | null;
  createdAt: string;
  updatedAt: string;
  uploadedCount: number;
  requestedCount: number;
  failedCount: number;
  items: StoredChatShort[];
};

type ChatRunStore = {
  chatId: string;
  updatedAt: string;
  batches: StoredChatBatch[];
};

const CHAT_RUN_PREFIX = "draftr-chat-run:";

export function buildChatShortsPath(chatId: string) {
  return `/shorts?chat=${encodeURIComponent(chatId)}`;
}

export function saveChatBatchToStorage(chatId: string, batch: StoredChatBatch) {
  if (typeof window === "undefined") {
    return;
  }
  const key = storageKey(chatId);
  const existing = loadChatRunFromStorage(chatId);
  const next: ChatRunStore = existing ?? { chatId, updatedAt: batch.updatedAt, batches: [] };
  const filtered = next.batches.filter(candidate => candidate.batchId !== batch.batchId);
  const merged = [batch, ...filtered].sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt));
  const payload: ChatRunStore = {
    chatId,
    updatedAt: batch.updatedAt,
    batches: merged,
  };
  window.localStorage.setItem(key, JSON.stringify(payload));
}

export function loadChatRunFromStorage(chatId: string): ChatRunStore | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(storageKey(chatId));
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as ChatRunStore;
  } catch {
    return null;
  }
}

export function loadChatShorts(chatId: string): StoredChatShort[] {
  const run = loadChatRunFromStorage(chatId);
  if (!run) {
    return [];
  }
  return run.batches
    .flatMap(batch => batch.items)
    .sort((left, right) => {
      const batchCompare = Date.parse(right.createdAt) - Date.parse(left.createdAt);
      if (batchCompare !== 0) {
        return batchCompare;
      }
      return left.itemIndex - right.itemIndex;
    });
}

function storageKey(chatId: string) {
  return `${CHAT_RUN_PREFIX}${chatId}`;
}

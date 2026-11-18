"use client";

import { useSyncExternalStore } from "react";

let currentTime = 0;
let timer: ReturnType<typeof setInterval> | undefined;
const listeners = new Set<() => void>();
function subscribe(callback: () => void) {
  listeners.add(callback);
  if (!timer) {
    currentTime = Date.now();
    timer = setInterval(() => { currentTime = Date.now(); listeners.forEach((listener) => listener()); }, 1000);
  }
  return () => { listeners.delete(callback); if (listeners.size === 0) { clearInterval(timer); timer = undefined; } };
}
export function useBrowserClock() {
  return useSyncExternalStore(subscribe, () => currentTime, () => 0);
}

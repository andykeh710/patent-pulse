"use client";

import { useCallback, useRef, useState } from "react";

/**
 * Hook for async actions that prevents duplicate concurrent execution.
 * Uses a ref-based guard so there is no race window between rapid clicks
 * and React's async state batching.
 *
 * Returns [execute, isRunning] where execute wraps the action safely.
 */
export function useAsyncAction(
  action: () => Promise<void>
): [() => Promise<void>, boolean] {
  const [isRunning, setIsRunning] = useState(false);
  const guardRef = useRef(false);

  const execute = useCallback(async () => {
    if (guardRef.current) return;
    guardRef.current = true;
    setIsRunning(true);
    try {
      await action();
    } finally {
      guardRef.current = false;
      setIsRunning(false);
    }
  }, [action]);

  return [execute, isRunning];
}

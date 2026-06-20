"use client";

import { useMemo } from "react";

interface DiversifiedFeedOptions<T> {
  typeOf: (item: T) => string;
  maxConsecutive?: number;
  maxShareOfType?: number;
  backfill?: T[];
}

export function useDiversifiedFeed<T>(
  items: T[],
  opts: DiversifiedFeedOptions<T>
): T[] {
  const { typeOf, maxConsecutive = 2, maxShareOfType = 0.4, backfill } = opts;

  return useMemo(() => {
    return diversify(items, typeOf, maxConsecutive, maxShareOfType, backfill);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, backfill]);
}

export function diversify<T>(
  items: T[],
  typeOf: (item: T) => string,
  maxConsecutive: number = 2,
  maxShareOfType: number = 0.4,
  backfill?: T[]
): T[] {
  if (items.length === 0) return [];

  // Build pool: items + backfill (deduped by typeOf)
  const pool = [...items];
  if (backfill) {
    const itemTypes = new Set(items.map(typeOf));
    for (const bf of backfill) {
      if (!itemTypes.has(typeOf(bf))) {
        pool.push(bf);
      }
    }
  }

  // Group by type
  const groups = new Map<string, T[]>();
  for (const item of pool) {
    const type = typeOf(item);
    const group = groups.get(type) || [];
    group.push(item);
    groups.set(type, group);
  }

  const sortedGroups = [...groups.entries()].sort(
    (a, b) => b[1].length - a[1].length
  );

  const targetLen = items.length;
  const result: T[] = [];
  const consumed = new Map<string, number>();
  const consecCount = new Map<string, number>();
  let lastType = "";

  while (result.length < targetLen) {
    let placed = false;

    // Prefer type with fewest consecutive placements among types that
    // can still be placed (respect both constraints)
    const candidates = sortedGroups
      .filter(([type, group]) => {
        const taken = consumed.get(type) || 0;
        if (taken >= group.length) return false;
        const cons = consecCount.get(type) || 0;
        if (cons >= maxConsecutive) return false;
        const share = taken / Math.max(targetLen, 1);
        if (share >= maxShareOfType) return false;
        return true;
      })
      .sort((a, b) => {
        // Prefer types with lower consecutive count
        const consA = consecCount.get(a[0]) || 0;
        const consB = consecCount.get(b[0]) || 0;
        if (consA !== consB) return consA - consB;
        // Prefer types with lower share
        const shareA = (consumed.get(a[0]) || 0) / targetLen;
        const shareB = (consumed.get(b[0]) || 0) / targetLen;
        return shareA - shareB;
      });

    if (candidates.length > 0) {
      const [type, group] = candidates[0];
      const taken = consumed.get(type) || 0;
      result.push(group[taken]);
      consumed.set(type, taken + 1);
      consecCount.set(type, (consecCount.get(type) || 0) + 1);
      for (const [other] of sortedGroups) {
        if (other !== type) consecCount.set(other, 0);
      }
      lastType = type;
      placed = true;
    }

    // Relax: allow maxConsecutive constraint to be broken, but NOT maxShareOfType
    if (!placed) {
      const relaxed = sortedGroups
        .filter(([type, group]) => {
          const taken = consumed.get(type) || 0;
          if (taken >= group.length) return false;
          const share = taken / Math.max(targetLen, 1);
          if (share >= maxShareOfType) return false;
          return true;
        })
        .sort((a, b) => {
          const shareA = (consumed.get(a[0]) || 0) / targetLen;
          const shareB = (consumed.get(b[0]) || 0) / targetLen;
          return shareA - shareB;
        });

      if (relaxed.length > 0) {
        const [type, group] = relaxed[0];
        const taken = consumed.get(type) || 0;
        result.push(group[taken]);
        consumed.set(type, taken + 1);
        consecCount.set(type, (consecCount.get(type) || 0) + 1);
        for (const [other] of sortedGroups) {
          if (other !== type) consecCount.set(other, 0);
        }
        lastType = type;
        placed = true;
      }
    }

    // Absolute last resort: break ALL constraints
    if (!placed) {
      for (const [type, group] of sortedGroups) {
        const taken = consumed.get(type) || 0;
        if (taken < group.length) {
          result.push(group[taken]);
          consumed.set(type, taken + 1);
          consecCount.set(type, (consecCount.get(type) || 0) + 1);
          for (const [other] of sortedGroups) {
            if (other !== type) consecCount.set(other, 0);
          }
          lastType = type;
          placed = true;
          break;
        }
      }
    }

    if (!placed) break;
  }

  return result;
}

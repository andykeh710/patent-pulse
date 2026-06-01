"use client";

import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-[var(--bg-glass)]",
        className
      )}
    />
  );
}

export function PatentCardSkeleton() {
  return (
    <div className="bg-[var(--bg-glass)] backdrop-blur-md rounded-lg border border-[var(--border-subtle)] p-4">
      <div className="flex justify-between items-start mb-3">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
      <Skeleton className="h-4 w-full mb-2" />
      <Skeleton className="h-4 w-2/3 mb-4" />
      <div className="flex gap-2">
        <Skeleton className="h-5 w-20 rounded-full" />
        <Skeleton className="h-5 w-24 rounded-full" />
      </div>
    </div>
  );
}

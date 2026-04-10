"use client";

interface StatusBarProps {
  totalEvents: number;
  lastReceivedAt: string | null;
}

export default function StatusBar({ totalEvents, lastReceivedAt }: StatusBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-6 rounded-xl border border-gray-200 bg-white px-5 py-3 shadow-sm text-sm">
      <div className="flex items-center gap-2">
        <span className="text-gray-400">受信イベント総数</span>
        <span className="text-xl font-bold text-blue-600 tabular-nums">
          {totalEvents.toLocaleString()}
        </span>
      </div>
      <div className="h-4 w-px bg-gray-200" />
      <div className="flex items-center gap-2">
        <span className="text-gray-400">最終受信時刻</span>
        <span className="font-medium text-gray-700 tabular-nums">
          {lastReceivedAt ?? "—"}
        </span>
      </div>
    </div>
  );
}

"use client";

import { useCallback, useState } from "react";
import LiveEventTable, { ArubaEvent } from "@/components/LiveEventTable";
import APMonitoringTable, { APEvent }  from "@/components/APMonitoringTable";
import StatusBar from "@/components/StatusBar";

type TabId = "audit" | "ap";

const TABS: { id: TabId; label: string }[] = [
  { id: "audit", label: "Audit Trail Events" },
  { id: "ap",    label: "AP Monitoring Events" },
];

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<TabId>("audit");

  const [auditTotal,  setAuditTotal]  = useState(0);
  const [auditLast,   setAuditLast]   = useState<string | null>(null);
  const [apTotal,     setApTotal]     = useState(0);
  const [apLast,      setApLast]      = useState<string | null>(null);

  const handleAudit = useCallback((e: ArubaEvent) => {
    setAuditTotal((n) => n + 1);
    setAuditLast(e.timestamp);
  }, []);

  const handleAP = useCallback((e: APEvent) => {
    setApTotal((n) => n + 1);
    setApLast(e.timestamp);
  }, []);

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-6xl space-y-4">

        {/* ヘッダー */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Aruba Central Streaming Dashboard
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">リアルタイムモニター</p>
        </div>

        {/* タブ */}
        <div className="flex gap-1 rounded-xl bg-gray-100 p-1 w-fit">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ステータスバー */}
        <StatusBar
          totalEvents={activeTab === "audit" ? auditTotal : apTotal}
          lastReceivedAt={activeTab === "audit" ? auditLast : apLast}
        />

        {/* コンテンツ（両方マウント・片方を非表示にすることで接続を維持） */}
        <div className={activeTab === "audit" ? "" : "hidden"}>
          <LiveEventTable onEvent={handleAudit} />
        </div>
        <div className={activeTab === "ap" ? "" : "hidden"}>
          <APMonitoringTable onEvent={handleAP} />
        </div>

      </div>
    </main>
  );
}

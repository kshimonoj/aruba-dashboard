"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface APEvent {
  id: number;
  timestamp: string;
  raw: string;
  msgClass: string;
  serial: string;
  mac: string;
  status: string;
}

interface APMonitoringTableProps {
  onEvent: (event: APEvent) => void;
}

const WS_URL    = `${process.env.NEXT_PUBLIC_BACKEND_URL ?? "ws://localhost:8001"}/ws/ap-events`;
const MAX_EVENTS = 100;

// ── ユーティリティ ──────────────────────────────────────────

function parseEvent(id: number, raw: string): APEvent {
  const now = new Date().toLocaleTimeString("ja-JP", { hour12: false });
  try {
    const obj     = JSON.parse(raw);
    const fields  = obj.fields ?? {};
    return {
      id,
      timestamp: now,
      raw,
      msgClass: obj.msg_class  ?? obj.format ?? "unknown",
      serial:   fields.serial_number ?? "—",
      mac:      fields.mac_address   ?? "—",
      status:   fields.status        ?? fields.operation ?? "—",
    };
  } catch {
    return { id, timestamp: now, raw, msgClass: "unknown", serial: "—", mac: "—", status: "—" };
  }
}

const MSG_CLASS_BADGE: Record<string, string> = {
  APInfo:       "bg-blue-100 text-blue-700",
  APSystemStat: "bg-indigo-100 text-indigo-700",
  RadioInfo:    "bg-purple-100 text-purple-700",
  RadioStat:    "bg-violet-100 text-violet-700",
  VapInfo:      "bg-cyan-100 text-cyan-700",
  VapStat:      "bg-teal-100 text-teal-700",
  PortInfo:     "bg-orange-100 text-orange-700",
  PortStat:     "bg-amber-100 text-amber-700",
  WlanInfo:     "bg-green-100 text-green-700",
  TunnelInfo:   "bg-rose-100 text-rose-700",
};

const STATUS_BADGE: Record<string, string> = {
  UP:     "bg-green-100 text-green-700",
  DOWN:   "bg-red-100 text-red-700",
  ADD:    "bg-blue-100 text-blue-700",
  MODIFY: "bg-yellow-100 text-yellow-700",
  DELETE: "bg-red-100 text-red-700",
};

// ── 展開詳細 ────────────────────────────────────────────────

function APEventDetail({ raw }: { raw: string }) {
  interface Field { key: string; value: string }
  const fields: Field[] = [];
  try {
    const obj = JSON.parse(raw);
    const f   = obj.fields ?? {};
    const LABELS: [string, string][] = [
      ["イベント種別",   "operation"],
      ["シリアル番号",   "serial_number"],
      ["MACアドレス",   "mac_address"],
      ["デバイス名",     "device_name"],
      ["モデル",         "model"],
      ["IPアドレス",     "ip_v4"],
      ["ステータス",     "status"],
      ["稼働時間(s)",   "uptime"],
      ["FWバージョン",  "firmware_version"],
      ["ゾーン",         "zone"],
      ["国コード",       "country_code"],
      ["CPU使用率(%)",  "cpu_utilization"],
      ["メモリ(%)",     "memory_utilization"],
      ["消費電力(W)",   "power_consumption"],
      ["チャンネル",     "channel"],
      ["送信電力",       "transmit_power"],
      ["無線番号",       "radio_number"],
      ["バンド",         "band"],
      ["ESSID",          "essid"],
      ["BSSID",          "bssid"],
      ["VLAN",           "vlan"],
      ["トンネル名",     "tunnel_name"],
      ["ピアIP",         "peer_ip"],
      ["ポート名",       "port_name"],
    ];
    for (const [label, key] of LABELS) {
      if (f[key] !== undefined && f[key] !== null && f[key] !== "" && f[key] !== "—") {
        fields.push({ key: label, value: String(f[key]) });
      }
    }
  } catch { /* ignore */ }

  let detail: unknown = raw;
  try { detail = JSON.parse(raw); } catch { /* ignore */ }

  return (
    <tr className="bg-gray-50">
      <td colSpan={6} className="px-6 py-4 border-b border-gray-200">
        {fields.length > 0 && (
          <div className="mb-3 grid grid-cols-2 gap-x-10 gap-y-1 text-xs">
            {fields.map(({ key, value }) => (
              <div key={key} className="flex gap-2">
                <span className="text-gray-400 w-32 shrink-0">{key}</span>
                <span className="text-gray-800 font-medium">{value}</span>
              </div>
            ))}
          </div>
        )}
        <pre className="text-xs font-mono text-gray-700 bg-white border border-gray-200 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-all max-h-80">
          {typeof detail === "string" ? detail : JSON.stringify(detail, null, 2)}
        </pre>
      </td>
    </tr>
  );
}

// ── メインコンポーネント ────────────────────────────────────

export default function APMonitoringTable({ onEvent }: APMonitoringTableProps) {
  const [events, setEvents]       = useState<APEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [expanded, setExpanded]   = useState<Set<number>>(new Set());
  const counterRef = useRef(0);

  const toggleRow = useCallback((id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  useEffect(() => {
    let ws: WebSocket;
    let timer: ReturnType<typeof setTimeout>;

    function connect() {
      ws = new WebSocket(WS_URL);
      ws.onopen    = () => setConnected(true);
      ws.onmessage = (e: MessageEvent) => {
        const id    = ++counterRef.current;
        const raw   = typeof e.data === "string" ? e.data : "";
        const event = parseEvent(id, raw);
        setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS));
        onEvent(event);
      };
      ws.onclose = () => { setConnected(false); timer = setTimeout(connect, 3000); };
      ws.onerror = () => ws.close();
    }

    connect();
    return () => { clearTimeout(timer); ws?.close(); };
  }, [onEvent]);

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-700">AP Monitoring Events</h2>
        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
          connected ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"
        }`}>
          <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-green-500 animate-pulse" : "bg-red-500"}`} />
          {connected ? "接続中" : "切断"}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
            <tr>
              <th className="px-4 py-2 w-8"></th>
              <th className="px-4 py-2 text-left w-14">#</th>
              <th className="px-4 py-2 text-left w-24">時刻</th>
              <th className="px-4 py-2 text-left w-36">イベント種別</th>
              <th className="px-4 py-2 text-left w-36">シリアル番号</th>
              <th className="px-4 py-2 text-left">MACアドレス / ステータス</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {events.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400 text-sm">
                  AP Monitoringイベント待機中…
                </td>
              </tr>
            ) : (
              events.map((ev) => {
                const isOpen = expanded.has(ev.id);
                return (
                  <>
                    <tr
                      key={ev.id}
                      onClick={() => toggleRow(ev.id)}
                      className="cursor-pointer hover:bg-blue-50 transition-colors select-none"
                    >
                      <td className="pl-4 pr-1 py-2 text-gray-400 text-xs">{isOpen ? "▾" : "▸"}</td>
                      <td className="px-4 py-2 text-gray-400 tabular-nums">{ev.id}</td>
                      <td className="px-4 py-2 text-gray-500 tabular-nums">{ev.timestamp}</td>
                      <td className="px-4 py-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${MSG_CLASS_BADGE[ev.msgClass] ?? "bg-gray-100 text-gray-500"}`}>
                          {ev.msgClass}
                        </span>
                      </td>
                      <td className="px-4 py-2 font-mono text-gray-700 text-xs">{ev.serial}</td>
                      <td className="px-4 py-2 text-gray-600 text-xs flex items-center gap-2">
                        <span className="font-mono">{ev.mac}</span>
                        {ev.status !== "—" && (
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[ev.status] ?? "bg-gray-100 text-gray-500"}`}>
                            {ev.status}
                          </span>
                        )}
                      </td>
                    </tr>
                    {isOpen && <APEventDetail key={`ap-detail-${ev.id}`} raw={ev.raw} />}
                  </>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

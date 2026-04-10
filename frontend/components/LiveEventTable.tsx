"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface ArubaEvent {
  id: number;
  timestamp: string;
  raw: string;
  format: string;
}

interface LiveEventTableProps {
  onEvent: (event: ArubaEvent) => void;
}

const WS_URL = "ws://192.168.19.150:8000/ws/events";
const MAX_EVENTS = 100;

// ---------------------------------------------------------------
// ユーティリティ
// ---------------------------------------------------------------

function getFormat(raw: string): string {
  try { return JSON.parse(raw).format ?? "unknown"; }
  catch { return "text"; }
}

/** 1行サマリー：意味のあるフィールドを優先抽出 */
function getSummary(raw: string): string {
  try {
    const envelope = JSON.parse(raw);

    // protobuf 抽出文字列
    if (envelope.format === "protobuf" && envelope.strings?.length) {
      return envelope.strings.join(" | ");
    }

    // binary
    if (envelope.format === "binary") {
      return `[binary ${envelope.size} bytes] ${envelope.hex?.slice(0, 40)}…`;
    }

    // JSON ペイロード
    const d = envelope.data ?? envelope;
    const candidates = [
      d?.event_type, d?.eventType, d?.type,
      d?.message, d?.msg,
      d?.action, d?.operation,
    ].filter(Boolean);
    if (candidates.length) return String(candidates[0]);

    return JSON.stringify(d).slice(0, 120);
  } catch {
    return raw.slice(0, 120);
  }
}

/** 展開時に表示するオブジェクト */
function getDetailObject(raw: string): unknown {
  try {
    const envelope = JSON.parse(raw);
    if (envelope.format === "json" && envelope.data !== undefined) return envelope.data;
    return envelope;
  } catch {
    return raw;
  }
}

/** JSONから意味フィールドを抽出して {key, value}[] を返す */
function extractFields(raw: string): { key: string; value: string }[] {
  try {
    const envelope = JSON.parse(raw);
    const d = (envelope.format === "json" ? envelope.data : envelope) ?? {};

    const FIELD_MAP: [string, string[]][] = [
      ["イベントタイプ", ["event_type", "eventType", "type", "action", "operation"]],
      ["タイムスタンプ",  ["timestamp", "time", "created_at", "createdAt", "event_time"]],
      ["ソース",         ["source", "src", "client_ip", "clientIp", "device", "ap_name"]],
      ["ユーザー",       ["user", "username", "user_name", "subject", "operator"]],
      ["メッセージ",     ["message", "msg", "description", "detail"]],
    ];

    const result: { key: string; value: string }[] = [];
    for (const [label, keys] of FIELD_MAP) {
      for (const k of keys) {
        if (d[k] !== undefined && d[k] !== null && d[k] !== "") {
          result.push({ key: label, value: String(d[k]) });
          break;
        }
      }
    }
    return result;
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------
// 定数
// ---------------------------------------------------------------

const FORMAT_BADGE: Record<string, string> = {
  json:     "bg-blue-100 text-blue-700",
  protobuf: "bg-purple-100 text-purple-700",
  binary:   "bg-gray-100 text-gray-500",
  text:     "bg-green-100 text-green-700",
};

// ---------------------------------------------------------------
// 展開行コンポーネント
// ---------------------------------------------------------------

function EventDetail({ raw, format }: { raw: string; format: string }) {
  const fields = extractFields(raw);
  const detail = getDetailObject(raw);

  return (
    <tr className="bg-gray-50">
      <td colSpan={5} className="px-6 py-4 border-b border-gray-200">
        {/* 意味フィールド（オプション） */}
        {fields.length > 0 && (
          <div className="mb-3 grid grid-cols-2 gap-x-8 gap-y-1 text-xs">
            {fields.map(({ key, value }) => (
              <div key={key} className="flex gap-2">
                <span className="text-gray-400 w-28 shrink-0">{key}</span>
                <span className="text-gray-800 font-medium truncate">{value}</span>
              </div>
            ))}
          </div>
        )}

        {/* 整形 JSON */}
        <pre className="text-xs font-mono text-gray-700 bg-white border border-gray-200 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-all max-h-96">
          {typeof detail === "string"
            ? detail
            : JSON.stringify(detail, null, 2)}
        </pre>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------
// メインコンポーネント
// ---------------------------------------------------------------

export default function LiveEventTable({ onEvent }: LiveEventTableProps) {
  const [events, setEvents]       = useState<ArubaEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [expanded, setExpanded]   = useState<Set<number>>(new Set());
  const wsRef      = useRef<WebSocket | null>(null);
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
    let reconnectTimer: ReturnType<typeof setTimeout>;

    function connect() {
      ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen  = () => setConnected(true);

      ws.onmessage = (e: MessageEvent) => {
        const id     = ++counterRef.current;
        const now    = new Date().toLocaleTimeString("ja-JP", { hour12: false });
        const raw    = typeof e.data === "string" ? e.data : "";
        const format = getFormat(raw);
        const event: ArubaEvent = { id, timestamp: now, raw, format };
        setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS));
        onEvent(event);
      };

      ws.onclose = () => {
        setConnected(false);
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => ws.close();
    }

    connect();
    return () => { clearTimeout(reconnectTimer); ws?.close(); };
  }, [onEvent]);

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      {/* ヘッダー */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-700">Audit Trail Events</h2>
        <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
          connected ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"
        }`}>
          <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-green-500 animate-pulse" : "bg-red-500"}`} />
          {connected ? "接続中" : "切断"}
        </span>
      </div>

      {/* テーブル */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
            <tr>
              <th className="px-4 py-2 text-left w-8"></th>
              <th className="px-4 py-2 text-left w-14">#</th>
              <th className="px-4 py-2 text-left w-24">時刻</th>
              <th className="px-4 py-2 text-left w-24">形式</th>
              <th className="px-4 py-2 text-left">概要</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {events.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-400 text-sm">
                  イベント待機中…
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
                      {/* 展開アイコン */}
                      <td className="pl-4 pr-1 py-2 text-gray-400 text-xs">
                        {isOpen ? "▾" : "▸"}
                      </td>
                      <td className="px-4 py-2 text-gray-400 tabular-nums">{ev.id}</td>
                      <td className="px-4 py-2 text-gray-500 tabular-nums">{ev.timestamp}</td>
                      <td className="px-4 py-2">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${FORMAT_BADGE[ev.format] ?? "bg-gray-100 text-gray-500"}`}>
                          {ev.format}
                        </span>
                      </td>
                      <td className="px-4 py-2 font-mono text-gray-700 truncate max-w-xl">
                        {getSummary(ev.raw)}
                      </td>
                    </tr>
                    {isOpen && <EventDetail key={`detail-${ev.id}`} raw={ev.raw} format={ev.format} />}
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

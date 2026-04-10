"""
decoder.py
- decode_message()    : Audit Trail （JSON or protobuf string 抽出）
- decode_ap_message() : AP Monitoring （CloudEvents protobuf envelope 解析）
"""
import json
import struct
from typing import Any, Dict, List, Optional, Tuple

# ── CloudEvents type → msg_class ──────────────────────────────
_AP_EVENT_TYPE_MAP = {
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.state.device":               "APInfo",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.state.radio":                "RadioInfo",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.state.port":                 "PortInfo",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.state.virtual_access_point": "VapInfo",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.state.wlan":                 "WlanInfo",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.state.tunnel":               "TunnelInfo",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.stats.device":               "APSystemStat",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.stats.radio":                "RadioStat",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.stats.virtual_access_point": "VapStat",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.stats.port":                 "PortStat",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.stats.modem":                "ModemStat",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.stats.tunnel":               "TunnelStat",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.stats.ip_probe":             "IPProbeStat",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.stats.user_role":            "RoleStat",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.stats.ssid":                 "SsidStat",
    "com.hpe.greenlake.network-monitoring.v1alpha1.aps.stats.vlan":                 "VlanStat",
}

# ── Field maps: {field_num: (name, wire_hint)} ────────────────
# wire_hint: "str"=string, "int"=varint, "float"=fixed32,
#            "double"=fixed64, "msg"=nested msg
_FIELD_MAPS: Dict[str, Dict[int, Tuple[str, str]]] = {
    "APInfo": {
        1:  ("operation",        "int"),
        2:  ("timestamp",        "str"),
        3:  ("tenant_id",        "str"),
        4:  ("serial_number",    "str"),
        5:  ("mac_address",      "str"),
        6:  ("device_name",      "str"),
        7:  ("model",            "str"),
        8:  ("ip_v4",            "str"),
        9:  ("ip_v6",            "str"),
        10: ("public_ip",        "str"),
        11: ("uptime",           "int"),
        12: ("mode",             "int"),
        13: ("status",           "int"),
        14: ("operating_mode",   "int"),
        16: ("elected_role",     "int"),
        17: ("mesh_mode",        "int"),
        18: ("current_uplink",   "int"),
        19: ("firmware_version", "str"),
        20: ("zone",             "str"),
        22: ("country_code",     "str"),
        23: ("down_reason",      "int"),
    },
    "APSystemStat": {
        1: ("timestamp",           "str"),
        2: ("tenant_id",           "str"),
        3: ("serial_number",       "str"),
        4: ("mac_address",         "str"),
        5: ("cpu_utilization",     "float"),
        6: ("memory_utilization",  "float"),
        7: ("power_consumption",   "double"),
    },
    "RadioInfo": {
        1:  ("operation",         "int"),
        2:  ("timestamp",         "str"),
        3:  ("tenant_id",         "str"),
        4:  ("serial_number",     "str"),
        5:  ("mac_address",       "str"),
        6:  ("radio_mac_address", "str"),
        7:  ("channel",           "int"),
        8:  ("transmit_power",    "int"),
        9:  ("radio_number",      "int"),
        10: ("band",              "int"),
        12: ("mode",              "int"),
        13: ("status",            "int"),
    },
    "RadioStat": {
        1:  ("timestamp",          "str"),
        2:  ("tenant_id",          "str"),
        3:  ("serial_number",      "str"),
        4:  ("mac_address",        "str"),
        5:  ("radio_mac_address",  "str"),
        6:  ("band",               "int"),
        8:  ("tx_bytes",           "int"),
        9:  ("rx_bytes",           "int"),
        10: ("noise_floor",        "int"),
        11: ("channel_quality",    "int"),
        12: ("total_utilization",  "int"),
        13: ("tx_utilization",     "int"),
        14: ("rx_utilization",     "int"),
    },
    "VapInfo": {
        1: ("operation",         "int"),
        2: ("timestamp",         "str"),
        3: ("tenant_id",         "str"),
        4: ("serial_number",     "str"),
        5: ("mac_address",       "str"),
        6: ("radio_mac_address", "str"),
        7: ("bssid",             "str"),
        8: ("essid",             "str"),
    },
    "VapStat": {
        1: ("timestamp",         "str"),
        2: ("tenant_id",         "str"),
        3: ("serial_number",     "str"),
        4: ("mac_address",       "str"),
        5: ("radio_mac_address", "str"),
        6: ("bssid",             "str"),
        7: ("essid",             "str"),
        8: ("tx_bytes",          "int"),
        9: ("rx_bytes",          "int"),
    },
    "WlanInfo": {
        1:  ("operation",    "int"),
        2:  ("timestamp",    "str"),
        3:  ("tenant_id",    "str"),
        4:  ("serial_number","str"),
        5:  ("mac_address",  "str"),
        6:  ("essid",        "str"),
        7:  ("vlan",         "int"),
        13: ("status",       "int"),
    },
    "PortInfo": {
        1: ("operation",    "int"),
        2: ("timestamp",    "str"),
        3: ("tenant_id",    "str"),
        4: ("serial_number","str"),
        5: ("mac_address",  "str"),
        6: ("port_index",   "int"),
        7: ("port_name",    "str"),
        9: ("status",       "int"),
    },
    "TunnelInfo": {
        1:  ("operation",    "int"),
        2:  ("timestamp",    "str"),
        3:  ("tenant_id",    "str"),
        4:  ("serial_number","str"),
        5:  ("mac_address",  "str"),
        7:  ("tunnel_name",  "str"),
        9:  ("peer_ip",      "str"),
        10: ("ip",           "str"),
        11: ("status",       "int"),
        14: ("peer_name",    "str"),
    },
    "IPProbeStat": {
        1:  ("timestamp",       "str"),
        2:  ("tenant_id",       "str"),
        3:  ("serial_number",   "str"),
        4:  ("mac_address",     "str"),
        6:  ("ip",              "str"),
        10: ("status",          "int"),
        11: ("loss_percentage", "float"),
        12: ("latency",         "float"),
        13: ("jitter",          "float"),
        14: ("mos",             "float"),
    },
    "ModemStat": {
        1: ("timestamp",        "str"),
        2: ("tenant_id",        "str"),
        3: ("serial_number",    "str"),
        4: ("mac_address",      "str"),
        5: ("tx_bytes",         "int"),
        6: ("rx_bytes",         "int"),
        7: ("cellular_signal",  "int"),
        8: ("cellular_sinr",    "int"),
    },
    "TunnelStat": {
        1:  ("timestamp",    "str"),
        2:  ("tenant_id",    "str"),
        3:  ("serial_number","str"),
        4:  ("mac_address",  "str"),
        6:  ("tunnel_name",  "str"),
        8:  ("tx_bytes",     "int"),
        9:  ("rx_bytes",     "int"),
        10: ("tx_pkts",      "int"),
        11: ("rx_pkts",      "int"),
    },
    "RoleStat": {
        1: ("timestamp",    "str"),
        2: ("tenant_id",    "str"),
        3: ("serial_number","str"),
        4: ("mac_address",  "str"),
        5: ("user_role",    "str"),
        6: ("tx_bytes",     "int"),
        7: ("rx_bytes",     "int"),
    },
    "SsidStat": {
        1: ("timestamp",    "str"),
        2: ("tenant_id",    "str"),
        3: ("serial_number","str"),
        4: ("mac_address",  "str"),
        5: ("ssid",         "str"),
        6: ("tx_bytes",     "int"),
        7: ("rx_bytes",     "int"),
    },
    "VlanStat": {
        1: ("timestamp",    "str"),
        2: ("tenant_id",    "str"),
        3: ("serial_number","str"),
        4: ("mac_address",  "str"),
        5: ("vlan",         "int"),
        6: ("tx_bytes",     "int"),
        7: ("rx_bytes",     "int"),
    },
    "PortStat": {
        1:  ("timestamp",    "str"),
        2:  ("tenant_id",    "str"),
        3:  ("serial_number","str"),
        4:  ("mac_address",  "str"),
        6:  ("port_index",   "int"),
        8:  ("tx_bytes",     "int"),
        9:  ("rx_bytes",     "int"),
        10: ("tx_pkts",      "int"),
        11: ("rx_pkts",      "int"),
    },
}

_OPERATION_NAMES = {0: "UNSPECIFIED", 1: "ADD", 2: "MODIFY", 3: "DELETE"}
_STATUS_NAMES    = {0: "UNSPECIFIED", 1: "UP", 2: "DOWN"}
_BAND_NAMES      = {0: "UNSPECIFIED", 1: "2GHz", 2: "5GHz", 3: "6GHz"}


# ── Public API ─────────────────────────────────────────────────

def decode_message(data: bytes) -> Dict[str, Any]:
    """Audit Trail メッセージのデコード"""
    if not data:
        return {"raw": "", "format": "empty"}
    try:
        obj = json.loads(data.decode("utf-8"))
        return {"data": obj, "format": "json"}
    except Exception:
        pass
    strings = _extract_protobuf_strings(data)
    if strings:
        return {"strings": strings, "format": "protobuf", "size": len(data)}
    return {"hex": data.hex(), "format": "binary", "size": len(data)}


def decode_ap_message(data: bytes) -> Dict[str, Any]:
    """
    AP Monitoring メッセージのデコード。
    CloudEvents protobuf envelope を解析して AP データを取り出す。
    """
    if not data:
        return {"format": "empty"}

    # CloudEvents protobuf envelope の解析
    ce = _parse_cloudevents_envelope(data)
    event_type = ce.get("type", "")
    msg_class  = _AP_EVENT_TYPE_MAP.get(event_type, "")

    # proto_data.value から AP メッセージバイトを取得
    ap_bytes: Optional[bytes] = ce.get("proto_data_value") or ce.get("binary_data")

    # type_url からも msg_class を補完
    if not msg_class:
        type_url = ce.get("proto_data_type_url", "")
        # e.g. "type.googleapis.com/ap.APSystemStat" → "APSystemStat"
        type_name = type_url.split("/")[-1].split(".")[-1] if type_url else ""
        if type_name in _FIELD_MAPS:
            msg_class = type_name

    result: Dict[str, Any] = {
        "format":     "ap_monitoring",
        "msg_class":  msg_class if msg_class else (event_type.split(".")[-1] if event_type else "unknown"),
        "event_type": event_type,
    }

    if ap_bytes and msg_class and msg_class in _FIELD_MAPS:
        decoded = _decode_protobuf_with_map(ap_bytes, _FIELD_MAPS[msg_class])
        result["fields"] = decoded
    elif ap_bytes:
        strings = _extract_protobuf_strings(ap_bytes)
        if strings:
            result["strings"] = strings
        result["size"] = len(ap_bytes)
    else:
        # envelope が取れなかった場合は文字列抽出にフォールバック
        strings = _extract_protobuf_strings(data)
        result["strings"] = strings if strings else []
        result["size"]    = len(data)

    return result


# ── Internal: CloudEvents protobuf envelope ────────────────────

def _parse_cloudevents_envelope(data: bytes) -> Dict[str, Any]:
    """
    CloudEvents protobuf format:
      field 1 (str) : id
      field 2 (str) : source
      field 3 (str) : spec_version
      field 4 (str) : type       ← イベントクラス名
      field 5 (map) : attributes （subject など）
      field 6 (bytes): binary_data
      field 7 (str) : text_data
      field 8 (bytes): proto_data (google.protobuf.Any)
    """
    result: Dict[str, Any] = {}
    i, length = 0, len(data)

    while i < length:
        try:
            tag, i = _read_varint(data, i)
            field_number = tag >> 3
            wire_type    = tag & 0x7

            if wire_type == 0:
                _, i = _read_varint(data, i)
            elif wire_type == 1:
                i += 8
            elif wire_type == 2:
                chunk_len, i = _read_varint(data, i)
                if i + chunk_len > length:
                    break
                chunk = data[i: i + chunk_len]
                i += chunk_len

                if field_number == 4:    # type
                    result["type"] = chunk.decode("utf-8", errors="replace")
                elif field_number == 6:  # binary_data
                    result["binary_data"] = chunk
                elif field_number == 8:  # proto_data = google.protobuf.Any
                    any_parsed = _parse_proto_any(chunk)
                    result["proto_data_type_url"]  = any_parsed.get("type_url", "")
                    result["proto_data_value"]     = any_parsed.get("value", b"")
            elif wire_type == 5:
                i += 4
            else:
                break
        except Exception:
            break

    return result


def _parse_proto_any(data: bytes) -> Dict[str, Any]:
    """google.protobuf.Any: field 1 = type_url (str), field 2 = value (bytes)"""
    result: Dict[str, Any] = {}
    i, length = 0, len(data)

    while i < length:
        try:
            tag, i = _read_varint(data, i)
            field_number = tag >> 3
            wire_type    = tag & 0x7

            if wire_type == 0:
                _, i = _read_varint(data, i)
            elif wire_type == 1:
                i += 8
            elif wire_type == 2:
                chunk_len, i = _read_varint(data, i)
                if i + chunk_len > length:
                    break
                chunk = data[i: i + chunk_len]
                i += chunk_len
                if field_number == 1:
                    result["type_url"] = chunk.decode("utf-8", errors="replace")
                elif field_number == 2:
                    result["value"] = chunk
            elif wire_type == 5:
                i += 4
            else:
                break
        except Exception:
            break

    return result


# ── Internal: field-map protobuf decoder ──────────────────────

def _decode_protobuf_with_map(
    data: bytes, field_map: Dict[int, Tuple[str, str]]
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    i, length = 0, len(data)

    while i < length:
        try:
            tag, i = _read_varint(data, i)
            field_number = tag >> 3
            wire_type    = tag & 0x7
            field_info   = field_map.get(field_number)

            if wire_type == 0:          # varint
                val, i = _read_varint(data, i)
                if field_info and field_info[1] == "int":
                    result[field_info[0]] = val

            elif wire_type == 1:        # 64-bit (double)
                if i + 8 > length:
                    break
                raw8 = data[i: i + 8]
                i += 8
                if field_info and field_info[1] == "double":
                    result[field_info[0]] = round(struct.unpack("<d", raw8)[0], 2)

            elif wire_type == 2:        # length-delimited
                chunk_len, i = _read_varint(data, i)
                if i + chunk_len > length:
                    break
                chunk = data[i: i + chunk_len]
                i += chunk_len
                if field_info and field_info[1] == "str":
                    try:
                        text = chunk.decode("utf-8")
                        if text:
                            result[field_info[0]] = text
                    except UnicodeDecodeError:
                        pass
                elif field_info and field_info[1] == "msg":
                    result[field_info[0]] = _decode_protobuf_with_map(chunk, {})

            elif wire_type == 5:        # 32-bit (float)
                if i + 4 > length:
                    break
                raw4 = data[i: i + 4]
                i += 4
                if field_info and field_info[1] == "float":
                    result[field_info[0]] = round(struct.unpack("<f", raw4)[0], 2)

            else:
                break

        except Exception:
            break

    # enum → 人が読める値に変換
    if "operation" in result:
        result["operation"] = _OPERATION_NAMES.get(result["operation"], str(result["operation"]))
    if "status" in result:
        result["status"] = _STATUS_NAMES.get(result["status"], str(result["status"]))
    if "band" in result:
        result["band"] = _BAND_NAMES.get(result["band"], str(result["band"]))

    return result


# ── Internal: string extraction (fallback) ────────────────────

def _extract_protobuf_strings(data: bytes) -> List[str]:
    results: List[str] = []
    i, length = 0, len(data)
    while i < length:
        try:
            tag, i = _read_varint(data, i)
            wire_type = tag & 0x7
            if wire_type == 0:
                _, i = _read_varint(data, i)
            elif wire_type == 1:
                i += 8
            elif wire_type == 2:
                chunk_len, i = _read_varint(data, i)
                if i + chunk_len > length:
                    break
                chunk = data[i: i + chunk_len]
                i += chunk_len
                try:
                    text = chunk.decode("utf-8")
                    if _is_readable(text):
                        results.append(text)
                except UnicodeDecodeError:
                    results.extend(_extract_protobuf_strings(chunk))
            elif wire_type == 5:
                i += 4
            else:
                break
        except Exception:
            break
    return results


def _read_varint(data: bytes, pos: int) -> Tuple[int, int]:
    result, shift = 0, 0
    while True:
        if pos >= len(data):
            raise ValueError("Unexpected end of data")
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
        if shift > 63:
            raise ValueError("Varint too long")
    return result, pos


def _is_readable(text: str) -> bool:
    if len(text) < 2:
        return False
    control = sum(1 for c in text if ord(c) < 0x20 and c not in "\t\n\r")
    return control / len(text) < 0.1

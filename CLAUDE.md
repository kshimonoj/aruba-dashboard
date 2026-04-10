# Aruba Central Streaming Dashboard

## プロジェクト概要

- **プロジェクト名**: Aruba Central Streaming Dashboard
- **目的**: Aruba CentralにWebSocketで接続し、AP Monitoringデータをリアルタイム表示するダッシュボード

## 技術スタック

### バックエンド
- **フレームワーク**: Python FastAPI
- **役割**: WebSocket中継（Aruba Central ↔ フロントエンド）
- **ポート**: 8000

### フロントエンド
- **フレームワーク**: Next.js
- **役割**: リアルタイムデータ表示
- **ポート**: 3000

## アーキテクチャ

```
Aruba Central
    ↕ WebSocket
Backend (FastAPI :8000)
    ↕ WebSocket
Frontend (Next.js :3000)
```

## 機能

- Aruba CentralにWebSocketで接続
- AP Monitoring データの受信・中継
- リアルタイムダッシュボード表示

## ディレクトリ構成

```
aruba-dashboard/
├── backend/    # Python FastAPI アプリケーション
├── frontend/   # Next.js アプリケーション
└── CLAUDE.md   # このファイル
```

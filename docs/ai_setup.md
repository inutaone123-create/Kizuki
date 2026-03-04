# AI設定ガイド — Kizuki レポート機能

Kizuki のレポート機能は **OpenAI互換API** を使用して日報・週報・月報を AI 生成します。
AI 設定を行わなくても、テンプレートモードで動作します。

---

## サービス比較

| サービス | 料金 | 速度 | セットアップ | 推奨モデル |
|---------|------|------|------------|------------|
| [Groq](https://groq.com) | 無料枠あり | 高速（LPU） | API Key のみ | `llama3-8b-8192` |
| [OpenRouter](https://openrouter.ai) | 従量課金 | モデル依存 | API Key のみ | `meta-llama/llama-3-8b-instruct` |
| [OpenAI](https://platform.openai.com) | 従量課金 | 高品質 | API Key のみ | `gpt-4o-mini` |
| [Ollama](https://ollama.ai) | 無料（ローカル） | GPU依存 | ローカル実行 | `llama3`, `gemma2` |
| [LM Studio](https://lmstudio.ai) | 無料（ローカル） | GPU依存 | GUI起動 | モデル選択式 |

---

## 各サービスの設定手順

### Groq（推奨・無料枠あり）

1. https://console.groq.com でアカウント作成
2. 「API Keys」→「Create API Key」でキーを発行
3. Kizuki の設定画面に入力：
   - **Base URL**: `https://api.groq.com/openai/v1`
   - **API Key**: 発行したキー（`gsk_...`）
   - **Model**: `llama3-8b-8192`（または `mixtral-8x7b-32768`）

### OpenRouter

1. https://openrouter.ai でアカウント作成
2. 「Keys」→ API Key を発行
3. Kizuki の設定画面に入力：
   - **Base URL**: `https://openrouter.ai/api/v1`
   - **API Key**: 発行したキー（`sk-or-...`）
   - **Model**: `meta-llama/llama-3-8b-instruct:free`

### OpenAI

1. https://platform.openai.com/api-keys でキーを発行
2. Kizuki の設定画面に入力：
   - **Base URL**: `https://api.openai.com/v1`
   - **API Key**: 発行したキー（`sk-...`）
   - **Model**: `gpt-4o-mini`

### Ollama（ローカル）

1. https://ollama.ai からインストール
2. `ollama pull llama3` でモデルをダウンロード
3. `ollama serve` で起動（デフォルト: `http://localhost:11434`）
4. Kizuki の設定画面に入力：
   - **Base URL**: `http://localhost:11434/v1`
   - **API Key**: `ollama`（任意の文字列でOK）
   - **Model**: `llama3`

### LM Studio

1. https://lmstudio.ai からインストール
2. 「Local Server」タブでサーバーを起動
3. Kizuki の設定画面に入力：
   - **Base URL**: `http://localhost:1234/v1`
   - **API Key**: `lm-studio`（任意）
   - **Model**: LM Studio で選択したモデル名

---

## Kizuki での操作手順

1. **⚙ 設定** タブ → **🤖 AI設定** → **✏️ 編集**
2. Base URL / API Key / モデル名 を入力して **保存**
3. **📊 レポート** タブで日付を選択し **⚡ 生成**
4. 生成されたレポートは一覧に保存される。クリックして詳細表示

---

## テンプレートモードについて

AI 設定が未設定の場合、または AI 呼び出しに失敗した場合は、
**テンプレートモード**（`📋 テンプレ` バッジ）で動作します。

- メモ内容をそのまま挿入した雛形を生成
- `（記入してください）` 欄を手動で記入してご利用ください
- AI 設定後は同じ操作で **🤖 AI** バッジが付いた高品質なレポートが生成されます

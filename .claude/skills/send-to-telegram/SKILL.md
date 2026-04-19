---
name: send-to-telegram
description: Отправляет финальный твит из workspace/tweet_final.txt мне в Телеграм через Bot API. Текст твита — в теге <code> (для удобного копирования), под ним ссылка на источник, счётчик символов и имя источника. parse_mode=HTML, спецсимволы < > & экранируются. Пишет лог в workspace/drafts.log.
---

# send-to-telegram

## Что делает

- Читает `workspace/tweet_final.txt` (после humanizer).
- Читает топ-1 из `workspace/news.json` для ссылки и источника.
- Экранирует `<`, `>`, `&` в тексте.
- Собирает сообщение:
  ```
  <code>{tweet}</code>
  {url}
  {len} chars · {source}
  ```
- Шлёт через `https://api.telegram.org/bot<TOKEN>/sendMessage`
  с `parse_mode=HTML`, `disable_web_page_preview=false`.
- Токен и chat_id — из `.env`
  (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).
- Лог в `workspace/drafts.log` (одна строка на отправку).

## Запуск

```bash
python .claude/skills/send-to-telegram/send.py
```

## Дедуп и лимит

- Сверяется с `workspace/seen.json` (48 часов).
- Если URL/заголовок уже отправлялся — молча выходит.
- Если за последние 24 часа в `drafts.log` уже 6 отправок —
  тоже молча выходит.

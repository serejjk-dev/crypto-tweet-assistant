---
name: fetch-crypto-news
description: Параллельно тянет крипто-новости из 4 бесплатных источников (CryptoPanic RSS, CryptoCompare News API, CoinDesk RSS, Decrypt RSS), объединяет, дедуплицирует по нормализованному заголовку, отбрасывает старше 12 часов и выбирает топ-3 самых интересных.
---

# fetch-crypto-news

## Источники (все бесплатны, без ключа)

- CryptoPanic RSS: `https://cryptopanic.com/news/rss/`
- CryptoCompare News API: `https://min-api.cryptocompare.com/data/v2/news/?lang=EN`
- CoinDesk RSS: `https://www.coindesk.com/arc/outboundfeeds/rss/`
- Decrypt RSS: `https://decrypt.co/feed`

## Что делает

1. Тянет все 4 источника параллельно (ThreadPoolExecutor).
2. Парсит в общий формат: `title, url, source, summary, published_at`.
3. Дедуп по нормализованному заголовку (lower, без пунктуации).
4. Отбрасывает всё старше 12 часов.
5. Считает скор и выбирает топ-3.
6. Сохраняет в `workspace/news.json`.

## Скор «интересности»

- +3 за громкий глагол в заголовке: hacked, launches, approves, sues,
  lists, delists, pumps, crashes, partners, files, rugs, freezes, bans.
- +2 за крупный тикер: BTC, ETH, SOL, XRP (+их имена).
- +1 за свежесть < 3 часов.

## Запуск

```bash
python .claude/skills/fetch-crypto-news/fetch.py
```

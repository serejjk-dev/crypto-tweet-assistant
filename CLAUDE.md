# Crypto Twitter Assistant

Помощник собирает свежие крипто-новости и присылает мне в Телеграм
готовые твиты для ручной публикации.

## Пайплайн

1. **fetch-crypto-news** — параллельно опрашивает 13 источников:
   Google News (6 запросов: crypto / defi / airdrop / swap-DEX /
   memecoin / X-swap), Reddit (r/CryptoCurrency, r/CryptoMoonShots),
   CoinGecko trending, CryptoCompare, CoinDesk, Decrypt, airdrops.io.
   Мёржит, убирает дубли по нормализованному заголовку и Jaccard,
   отбрасывает старше 12 часов, ранжирует с бонусами для
   airdrop / swap-DEX / trending тем и штрафом за «price prediction»
   шум. Результат: топ-3 в `workspace/news.json`.

2. **Выбор топ-1** из `workspace/news.json` (первый элемент,
   он самый интересный по скору).

3. **crypto-slang-tone** — переписывает выбранную новость в твит
   180–270 символов. Приоритет — **ясность новости**, не вайб.
   Структура: сначала факт (15–30 слов, без сленга, понятно
   человеку не из крипты), потом **одна** ироничная мысль,
   опционально короткий панчлайн. Сленг максимум **1 термин**
   на весь твит (ngmi / wagmi / rekt / probably nothing / few
   understand / ser), ноль — часто лучше. Никогда не начинать
   твит со сленга. Тикеры через `$`, макс 1 эмодзи, макс 1 хэштег.

4. **humanizer** — ОБЯЗАТЕЛЬНЫЙ шаг, никогда не пропускается.
   Чистит следы ИИ: запретные слова (delve, tapestry, realm,
   landscape, navigate, leverage, robust, seamless, game changer,
   revolutionary, unprecedented), запретные фразы, лишние
   "не X, а Y", em-dash → дефис/точка. Финал ≤ 270 символов
   вместе со ссылкой.

5. **send-to-telegram** — шлёт твит через Telegram Bot API.
   В `<code>`-теге текст твита, под ним ссылка на источник,
   счётчик символов и имя источника. Логирует в
   `workspace/drafts.log`.

## Правила

- Веди `workspace/seen.json` за последние 48 часов
  (url + нормализованный заголовок + оригинальный title).
  Дедуп в `fetch-crypto-news` по трём критериям:
  1) точное совпадение url,
  2) точное совпадение нормализованного заголовка,
  3) Jaccard-схожесть контентных слов ≥ 0.5
     (ловит одну и ту же новость от разных источников).
- Лимит: **6 драфтов в сутки** (считать по `drafts.log`).
  При превышении — тихо выходить.
- **Никогда не пропускать humanizer.** Даже если твит уже
  выглядит норм — прогнать через него.
- В Телеге под твитом идёт блок `hot take:` — моё ироничное
  мнение на новость в том же сленге. Генерируется в
  `crypto-slang-tone` из пула фраз по типу события (hack, pump,
  launch и т.д.), прогоняется через humanizer.
- Ключи берутся из `.env` или GitHub Secrets
  (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID).

## Зависимости

```bash
pip install requests feedparser python-dotenv
```

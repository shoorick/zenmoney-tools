# Обработка списка транзакций

В веб-приложении [MyCredo](https://mycredo.ge/) грузинского банка [Credo](https://credo.ge/) не работает экспорт транзакций, однако можно эти данные получить, пользуясь отладчиком браузера и потом преобразовать для дальнейшей работы.

## 1. Получение данных

- Открыть [MyCredo](https://mycredo.ge/), выполнить вход, перейти к [списку транзакций](https://mycredo.ge/home/transactions)
- Открыть инструменты разработчика (<kbd>F12</kbd>)
- Перейти на вкладку "Network"
- Убедиться, что запросы записываются, включить запись, если нет (<kbd>Ctrl+E</kbd>), Очистить историю (<kbd>Ctrl+L</kbd>)
- (_необязательно_) Включить фильтр типа **Fetch/XHR**
- На странице с транзакциями в блоке «Фильтр» выбрать диапазон дат и нажать красную кнопку «Фильтр»
- Пролистать страницу, чтобы все транзакции были загружены
- На панели инструментов, где находятся кнопки записи и очистки, в правой части есть кнопка загрузки (стрелка вниз) — нажать её и в открывшемся меню выбрать **Export as HAR (with sensitive data)...**, сохранить файл
- Если пункта **Export as HAR (with sensitive data)...** нет — исправить настройки отладчика: кнопка с шестерёнкой (Settings) → Preferences → в блоке Network отметить **Allow to generate HAR with sensitive data** — см. [документацию — Save all network requests to a HAR file](https://developer.chrome.com/docs/devtools/network/reference#save-as-har)

## 2. Преобразование данных

```sh
./extract-transactions-from-har.sh < 00.har > 03-merged.json
```

Альтернативный способ — пошагово:

### 2.1. Извлечение текстового содержимого ответов

```sh
jq -r '.log.entries[].response.content.text' 00.har > 01-responses.txt
perl -nle 'next unless /transactionPagingList/; print "$_,"' 01-responses.txt | perl -0777 -ne 's/,\s*$//; print "[\n$_\n]"' > 02-tx.json 
```

### 2.2. Объединение JSON

```sh
jq '[.[] | .data.transactionPagingList.itemList[]]' 02-tx.json > 03-merged.json
```

### Результат

В обоих случаях получается JSON вида
```json
[
  {
    "accountNumber": "GE54CD0xxxxxxxxxxxxxxx",
    "credit": null,
    "currency": "USD",
    "transactionType": "AccountWithdrawal",
    "transactionId": "FT25xxxxxxxx",
    "debit": 2.42,
    "description": "Payment - xxxxxxxxxx 22.02.2022",
    "isCardBlock": false,
    "operationDateTime": "2022-02-25T22:22:00",
    "stmtEntryId": "2xxxxxxxxxxxxxx.0xxxxx",
    "canRepeat": false,
    "canReverse": false,
    "canTemplate": false,
    "amountEquivalent": 42.42,
    "operationType": "Операция по карте",
    "operationTypeId": null
  },
  ...
]
```

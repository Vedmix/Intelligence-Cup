# Локальный поиск по тикетам RHEL

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python semantic_search.py index
HF_HUB_OFFLINE=1 .venv/bin/python semantic_search.py search 'Изменения схемы LDAP не доходят до реплики' --limit 5
.venv/bin/python search.py 'BZ#1759941' --limit 5
```

По умолчанию скрипты читают `../data/tickets`. Для базы Hermes добавьте `--tickets /root/base/tickets` к командам индексации и BM25. Пути в выдаче относительны к каталогу карточек. После изменений в карточках повторите `index`. Первый запуск загружает модель Hugging Face. Сходство показывает близость текста и не подтверждает причину сбоя.

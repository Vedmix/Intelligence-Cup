# Запуск локальной базы тикетов в WSL

Команды ниже рассчитаны на AlmaLinux 10 в WSL 2. Репозиторий содержит Markdown-карточки в `data/tickets`, скрипты в `hermes-rag` и готовый переносимый индекс в `hermes-rag/index`.

## 1. Откройте AlmaLinux

В Windows PowerShell выполните `wsl --list --verbose` и найдите имя дистрибутива AlmaLinux. Запустите его командой `wsl -d ИМЯ_ДИСТРИБУТИВА`. Если AlmaLinux отсутствует в списке, сначала установите или импортируйте дистрибутив в WSL 2.

Остальные команды выполняйте в терминале AlmaLinux под пользователем, который запускает Hermes. Используйте `sudo` для установки системных пакетов. Если работаете как root, опустите `sudo`.

## 2. Подготовьте репозиторий и Python

```bash
sudo dnf install -y git python3 python3-pip
git clone https://github.com/Vedmix/Test-Case.git ~/Test-Case
cd ~/Test-Case
python3 -m venv hermes-rag/.venv
hermes-rag/.venv/bin/python -m pip install -r hermes-rag/requirements.txt
```

Если репозиторий уже клонирован, перейдите в его каталог и обновите его через `git pull --ff-only origin main`. Для закрытого репозитория потребуется доступ на чтение.

## 3. Подготовьте индекс и проверьте поиск

Выполните из корня репозитория:

```bash
hermes-rag/.venv/bin/python hermes-rag/semantic_search.py index
ls -lh hermes-rag/index/{embeddings.npy,metadata.json}
hermes-rag/.venv/bin/python hermes-rag/search.py 'BZ#1759941' --limit 5
HF_HUB_OFFLINE=1 hermes-rag/.venv/bin/python hermes-rag/semantic_search.py search \
  'Directory Server: изменения схемы LDAP не реплицируются на второй сервер' --limit 5
```

При первом запуске E5 скачивает веса из Hugging Face. Индексация выполняется на CPU. Готовый индекс можно использовать сразу, если карточки соответствуют его версии, а веса уже есть в локальном кэше. После изменений в Markdown повторите команду `index`. Пути из JSON-выдачи относительны к `data/tickets`. Чтобы использовать отдельную базу, передайте `--tickets /root/base/tickets` при индексации и в BM25. При чтении результатов используйте тот же каталог.

## 4. Подключите Hermes

Сначала настройте Hermes и проверьте, что команда `hermes` доступна в AlmaLinux. Для модели DeepSeek используйте конфигурацию своего провайдера через `hermes setup`. В настройках Hermes должен быть доступен терминальный инструмент с локальным исполнением.

Запишите системный промпт в профиль Hermes. Эта команда заменяет текущий `SOUL.md`, предварительно сохраняя его копию.

```bash
cd ~/Test-Case
hermes_home="${HERMES_HOME:-$HOME/.hermes}"
mkdir -p "$hermes_home"
if [ -f "$hermes_home/SOUL.md" ]; then
  cp "$hermes_home/SOUL.md" "$hermes_home/SOUL.md.$(date +%Y%m%d-%H%M%S).bak"
fi
cp promts/system-prompt.md "$hermes_home/SOUL.md"
hermes
```

Запускайте Hermes из корня репозитория, чтобы относительные пути в промпте работали. Если используете отдельный каталог тикетов, поправьте команды и корень карточек в установленном `SOUL.md`.

В новой сессии отправьте тестовое обращение: «После изменения схемы Directory Server на RHEL 9.2 изменения LDAP не доходят до второй реплики». Проверьте, что Hermes вызвал локальный поиск, прочитал `data/tickets/BZ/BZ-1759941.md` и запросил сборку Directory Server, журналы и топологию, если этих данных нет. Совпадение карточки само по себе не подтверждает причину.

Индекс и поиск работают локально. При использовании облачной модели текст обращения и выдержки из карточек могут передаваться провайдеру модели.

[Конфигурация Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)

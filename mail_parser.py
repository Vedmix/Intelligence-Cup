
import os
import re
import base64
import html
from pathlib import Path
from email.header import decode_header, make_header

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from image_parser import analyze_image


# Папка проекта
BASE_DIR = Path(__file__).resolve().parent

# Пути к данным
TICKETS_DIR = BASE_DIR / "data" / "tickets"
ATTACHMENTS_DIR = BASE_DIR / "data" / "attachments"

# Gmail API
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


def decode_text(value):
    """Декодирует заголовки и текст письма."""

    if not value:
        return ""

    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def clean_filename(filename):
    """Очищает имя вложения от недопустимых символов."""

    filename = filename.replace("\\", "/")
    filename = filename.split("/")[-1]
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', "_", filename)

    return filename or "attachment"


def get_service():
    """Авторизация и подключение к Gmail API."""

    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES
        )

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE),
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build(
        "gmail",
        "v1",
        credentials=creds
    )


def decode_part(service, message_id, part):
    """Получает содержимое MIME-части письма."""

    body = part.get("body", {})
    data = body.get("data")

    if data:
        return base64.urlsafe_b64decode(data)

    attachment_id = body.get("attachmentId")

    if attachment_id:
        attachment = service.users().messages().attachments().get(
            userId="me",
            messageId=message_id,
            id=attachment_id
        ).execute()

        return base64.urlsafe_b64decode(
            attachment["data"]
        )

    return b""


def extract_email_data(service, message):
    """
    Извлекает текст письма и вложения.
    Возвращает текст, список вложений.
    """

    message_id = message["id"]
    payload = message.get("payload", {})

    text_parts = []
    html_parts = []
    attachments = []

    def process_parts(parts):

        for part in parts:

            filename = part.get("filename", "")
            mime_type = part.get("mimeType", "")

            # Обработка вложений
            if filename:

                filename = clean_filename(filename)

                try:
                    file_data = decode_part(
                        service,
                        message_id,
                        part
                    )

                    if not file_data:
                        print(
                            f"Пустое вложение пропущено: {filename}"
                        )
                        continue

                    # Папка создаётся только при наличии файла
                    attachment_dir = (
                        ATTACHMENTS_DIR / message_id
                    )

                    attachment_dir.mkdir(
                        parents=True,
                        exist_ok=True
                    )

                    # Защита от совпадения имён файлов
                    file_path = attachment_dir / filename

                    if file_path.exists():
                        stem = file_path.stem
                        suffix = file_path.suffix
                        counter = 1

                        while file_path.exists():
                            file_path = attachment_dir / (
                                f"{stem}_{counter}{suffix}"
                            )
                            counter += 1

                    with open(file_path, "wb") as file:
                        file.write(file_data)

                    attachments.append({
                        "name": file_path.name,
                        "path": file_path.relative_to(
                            BASE_DIR
                        ).as_posix(),
                        "full_path": file_path,
                        "mime_type": mime_type
                    })

                    print(f"Сохранено вложение: {filename}")

                except Exception as error:
                    print(
                        f"Ошибка сохранения {filename}: {error}"
                    )

            # Обработка текста письма
            elif mime_type == "text/plain":

                data = decode_part(
                    service,
                    message_id,
                    part
                )

                if data:
                    text_parts.append(
                        data.decode("utf-8", errors="replace")
                    )

            elif mime_type == "text/html":

                data = decode_part(
                    service,
                    message_id,
                    part
                )

                if data:
                    html_parts.append(
                        data.decode("utf-8", errors="replace")
                    )

            # Обработка вложенных MIME-частей
            if part.get("parts"):
                process_parts(part["parts"])

    process_parts([payload])

    # Предпочитаем обычный текст HTML
    if text_parts:
        email_text = "\n".join(text_parts)

    elif html_parts:
        email_text = "\n".join(html_parts)
        email_text = re.sub(
            r"<(script|style).*?</\1>",
            " ",
            email_text,
            flags=re.IGNORECASE | re.DOTALL
        )
        email_text = re.sub(
            r"<[^>]+>",
            " ",
            email_text
        )
        email_text = html.unescape(email_text)

    else:
        email_text = "Текст письма отсутствует."

    return email_text.strip(), attachments


def analyze_attachments(attachments):
    """Анализирует изображения через Qwen-VL."""

    results = []

    for attachment in attachments:

        mime_type = attachment["mime_type"]

        if not mime_type.startswith("image/"):
            continue

        try:
            description = analyze_image(
                attachment["full_path"]
            )

            results.append({
                "name": attachment["name"],
                "description": description,
                "success": True
            })

        except Exception as error:
            print(
                f"Не удалось проанализировать "
                f"{attachment['name']}: {error}"
            )

            results.append({
                "name": attachment["name"],
                "description": str(error),
                "success": False
            })

    return results


def create_ticket(service, message):
    """Создаёт Markdown-тикет из письма."""

    message_id = message["id"]

    TICKETS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    ticket_path = TICKETS_DIR / f"gmail_{message_id}.md"

    # Проверка повторной обработки
    if ticket_path.exists():
        print(f"Тикет уже существует: {message_id}")
        return

    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    headers_dict = {
        header["name"].lower(): header["value"]
        for header in headers
    }

    sender = decode_text(
        headers_dict.get("from", "Неизвестно")
    )

    subject = decode_text(
        headers_dict.get("subject", "Без темы")
    )

    date = headers_dict.get(
        "date",
        "Неизвестно"
    )

    print(f"\nОбрабатываем письмо: {subject}")

    # Извлечение текста и вложений
    email_text, attachments = extract_email_data(
        service,
        message
    )

    # Анализ изображений
    image_results = analyze_attachments(attachments)

    # Формирование Markdown
    md = [
        "# Обращение из электронной почты",
        "",
        "## Общая информация",
        "",
        "- **Источник:** Gmail",
        f"- **Отправитель:** {sender}",
        f"- **Тема:** {subject}",
        f"- **Дата письма:** {date}",
        f"- **ID письма:** {message_id}",
        "",
        "## Текст обращения",
        "",
        email_text,
        ""
    ]

    # Добавляем приложения только при наличии вложений
    if attachments:

        md.extend([
            "## Приложения",
            ""
        ])

        for index, attachment in enumerate(
            attachments,
            start=1
        ):

            md.extend([
                f"### {index}. {attachment['name']}",
                "",
                f"- **Путь:** `{attachment['path']}`",
                f"- **Тип:** {attachment['mime_type']}",
                ""
            ])

            # Добавляем описание изображения
            for result in image_results:

                if result["name"] == attachment["name"]:

                    md.extend([
                        "**Описание от Qwen-VL:**",
                        "",
                        result["description"],
                        ""
                    ])

                    if not result["success"]:
                        md.append(
                            "_Статус анализа: ошибка._"
                        )
                        md.append("")

    # Статус обработки
    md.extend([
        "## Статус обработки",
        "",
        "- **Gmail:** обработан",
        f"- **Вложения:** {len(attachments)}",
        f"- **Qwen-VL:** {'выполнен' if any(r['success'] for r in image_results) else 'не запускался или не завершён'}",
        ""
    ])

    # Сохранение тикета
    with open(
        ticket_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write("\n".join(md))

    print(f"Тикет создан: {ticket_path}")


def main():
    print("Подключаемся к Gmail...")

    try:
        service = get_service()

        print("Получаем последние письма из входящих...")

        results = service.users().messages().list(
            userId="me",
            q="in:inbox newer_than:7d",
            maxResults=10
        ).execute()

        messages = results.get("messages", [])

        if not messages:
            print("Новых писем не найдено.")
            return

        print(f"Найдено писем: {len(messages)}")

        for item in messages:

            message = service.users().messages().get(
                userId="me",
                id=item["id"],
                format="full"
            ).execute()

            create_ticket(service, message)

        print("\nОбработка писем завершена.")

    except HttpError as error:
        print(f"Ошибка Gmail API: {error}")

    except Exception as error:
        print(f"Ошибка: {error}")


if __name__ == "__main__":
    main()

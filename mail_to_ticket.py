
from googleapiclient.errors import HttpError

from mail_parser import get_service, create_ticket


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
            print("Писем не найдено.")
            return

        print(f"Найдено писем: {len(messages)}")

        processed = 0
        skipped = 0

        for item in messages:
            message_id = item["id"]

            print(f"\nОбрабатываем письмо: {message_id}")

            message = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()

            result = create_ticket(service, message)

            if result:
                processed += 1
            else:
                skipped += 1

        print("\n========== РЕЗУЛЬТАТ ==========")
        print(f"Создано тикетов: {processed}")
        print(f"Пропущено писем: {skipped}")
        print("Обработка завершена.")

    except HttpError as error:
        print(f"Ошибка Gmail API: {error}")

    except Exception as error:
        print(f"Ошибка обработки: {error}")


if __name__ == "__main__":
    main()

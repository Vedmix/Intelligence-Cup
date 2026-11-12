
import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent

TICKETS_DIR = BASE_DIR / "data" / "tickets"

TICKETS_FILE = BASE_DIR / "data" / "tickets.csv"
SOLUTIONS_FILE = BASE_DIR / "data" / "solutions.csv"


def get_field(text, field_name):
    """Извлекает значение из таблицы Markdown."""

    pattern = rf"\|\s*{re.escape(field_name)}\s*\|\s*(.*?)\s*\|"

    match = re.search(pattern, text)

    return match.group(1).strip() if match else ""


def get_section(text, section_name):
    """Извлекает содержимое раздела Markdown."""

    pattern = (
        rf"##\s+{re.escape(section_name)}\s*\n"
        rf"(.*?)(?=\n##\s+|\Z)"
    )

    match = re.search(
        pattern,
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    return match.group(1).strip() if match else ""


def clean_text(text):
    """Удаляет лишнюю Markdown-разметку."""

    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"^[-*]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n+", " ", text)

    return text.strip()



def parse_ticket(file_path):
    """Обрабатывает один Markdown-файл."""

    text = file_path.read_text(encoding="utf-8")

    ticket_id = get_field(text, "Тикет")

    # Проверяем, что это настоящий ID
    if not re.fullmatch(r"(BZ#\d+|RHEL-\d+)", ticket_id):
        return None, None

    if ticket_id.startswith("BZ#"):
        ticket_type = "BZ"
    else:
        ticket_type = "RHEL"

    ticket = {
        "ticket_id": ticket_id,
        "ticket_type": ticket_type,
        "component": get_field(text, "Компонент"),
        "status": get_field(text, "Статус"),
        "symptom": clean_text(
            get_section(text, "Симптом")
        ),
        "other_symptoms": clean_text(
            get_section(text, "Другие формулировки симптома")
        ),
        "diagnostics": clean_text(
            get_section(text, "Диагностические данные")
        ),
        "tracker_data": clean_text(
            get_section(text, "Данные из трекера")
        ),
        "manual_group": "",
        "agent_group": "",
        "manual_repeat": ""
    }

    solution = {
        "ticket_id": ticket_id,
        "solution": clean_text(
            get_section(text, "Решение")
        ),
        "fixed_release": get_field(
            text, "Релиз с исправлением"
        )
    }

    return ticket, solution


def save_csv(file_path, data, fieldnames):
    """Сохраняет данные в CSV."""

    with file_path.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            delimiter=";"
        )

        writer.writeheader()
        writer.writerows(data)


def main():

    if not TICKETS_DIR.exists():
        print("Папка с тикетами не найдена!")
        return

    files = sorted(TICKETS_DIR.rglob("*.md"))

    if not files:
        print("Markdown-файлы не найдены!")
        return

    tickets = []
    solutions = []

    
    for file_path in files:
        try:
            ticket, solution = parse_ticket(file_path)

            if ticket is None:
                print(f"Пропущен некорректный ID: {file_path.name}")
                continue

            tickets.append(ticket)

            solution["solution_id"] = (
                f"S-{len(solutions) + 1:04d}"
            )

            solutions.append(solution)

            if not solution["solution"]:
                print(f"Нет извлечённого решения: {ticket['ticket_id']}")

        except Exception as error:
            print(f"Ошибка обработки {file_path.name}: {error}")


    ticket_fields = [
        "ticket_id",
        "ticket_type",
        "component",
        "status",
        "symptom",
        "other_symptoms",
        "diagnostics",
        "tracker_data",
        "manual_group",
        "agent_group",
        "manual_repeat"
    ]

    solution_fields = [
        "solution_id",
        "ticket_id",
        "solution",
        "fixed_release"
    ]

    save_csv(TICKETS_FILE, tickets, ticket_fields)
    save_csv(SOLUTIONS_FILE, solutions, solution_fields)

    print("\nОбработка завершена!")
    print(f"Всего тикетов: {len(tickets)}")
    print(f"Найдено решений: {len(solutions)}")

    print(f"\nТаблица тикетов: {TICKETS_FILE}")
    print(f"Таблица решений: {SOLUTIONS_FILE}")


if __name__ == "__main__":
    main()

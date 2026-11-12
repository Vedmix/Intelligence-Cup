
import torch
from qwen_asr import Qwen3ASRModel
from pathlib import Path
from datetime import datetime

# Пути к файлам
audio_path = Path("data/1.mp3")
output_dir = Path("data/tickets")

# Проверяем наличие аудиозаписи
if not audio_path.exists():
    raise FileNotFoundError(f"Аудиофайл не найден: {audio_path}")

# Создаём папку для готовых тикетов
output_dir.mkdir(parents=True, exist_ok=True)

# Дата и время обработки
processing_time = datetime.now()
ticket_id = processing_time.strftime("%Y%m%d_%H%M%S")

print("Загружаем Qwen-ASR...")

model = Qwen3ASRModel.from_pretrained(
    "Qwen/Qwen3-ASR-0.6B",
    dtype=torch.float32,
    device_map="cpu",
    max_inference_batch_size=1,
    max_new_tokens=256,
)

print("Модель загружена!")
print("Начинаем распознавание аудио...")

# Распознаём речь
results = model.transcribe(
    audio=str(audio_path),
    language="Russian",
)

recognized_text = results[0].text

print("\nРаспознанный текст:")
print(recognized_text)

# Формируем содержимое Markdown
markdown_content = f"""# Обращение №{ticket_id}

## Общая информация

- **Источник:** Телефон
- **Дата обработки:** {processing_time.strftime("%d.%m.%Y %H:%M:%S")}
- **Язык:** Русский
- **Модель распознавания:** Qwen3-ASR-0.6B
- **Исходный файл:** {audio_path.name}

## Текст обращения

{recognized_text}

## Вложения

- {audio_path.name}
"""

# Сохраняем тикет
output_path = output_dir / f"audio_ticket_{ticket_id}.md"
output_path.write_text(markdown_content, encoding="utf-8")

print("\nТикет успешно создан!")
print(f"Путь к файлу: {output_path}")

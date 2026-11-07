
import base64
import json
import urllib.request
from pathlib import Path


MODEL = "qwen2.5vl:3b"
API_URL = "http://localhost:11434/api/generate"


def analyze_image(image_path):
    """
    Передаёт изображение в Qwen-VL через Ollama.
    Возвращает текстовое описание изображения.
    """

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Изображение не найдено: {image_path}"
        )

    with open(image_path, "rb") as file:
        image_base64 = base64.b64encode(
            file.read()
        ).decode("utf-8")

    payload = {
        "model": MODEL,
        "prompt": (
            "Ты помощник службы технической поддержки. "
            "Проанализируй изображение. "
            "Опиши, что на нём изображено. "
            "Если присутствует текст, прочитай его. "
            "Выдели информацию, которая может помочь "
            "разобраться с обращением пользователя. "
            "Не придумывай отсутствующие сведения."
        ),
        "images": [image_base64],
        "stream": False,
        "options": {
            "num_ctx": 8192,
            "temperature": 0.2
        },
        "keep_alive": "5m"
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        }
    )

    print(f"Анализируем изображение: {image_path.name}")

    try:
        with urllib.request.urlopen(
            request,
            timeout=300
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

        description = result.get("response", "").strip()

        if not description:
            raise RuntimeError(
                "Qwen-VL вернула пустое описание."
            )

        print("Изображение успешно обработано.")

        return description

    except Exception as error:
        raise RuntimeError(
            f"Ошибка анализа изображения {image_path.name}: {error}"
        ) from error

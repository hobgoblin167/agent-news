import requests

LLM_URL = "http://127.0.0.1:8080/v1/chat/completions"


def summarize_article(article: dict) -> dict:
    text = article.get("text", "")

    if not text:
        article["summary"] = "Не удалось получить текст статьи."
        return article



    try:
        response = requests.post(
            LLM_URL,
            json={
                "model": "local-model",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 800
            },
            timeout=300
        )

        response.raise_for_status()

        data = response.json()

        article["summary"] = (
            data["choices"][0]["message"]["content"]
        )

    except Exception as e:
        print("Ошибка Qwen:", e)
        article["summary"] = "Ошибка суммаризации."

    return article
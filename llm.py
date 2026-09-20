import requests

LLM_URL = "http://127.0.0.1:8080/v1/chat/completions"


def summarize_article(article: list[dict]) -> str:
    combined_articles = []


    for i, article in enumerate(article, 1):

        text = article.get("text", "")

        if not text:
            continue

        combined_articles.append(
            f"""
        НОВОСТЬ {i}

        Заголовок:
        {article["title"]}

        Текст:
        {article["text"][:350]}
        """
        )

    combined_articles = "\n".join(combined_articles)
    prompt = f"""
    Ты новостной редактор.

    Ниже несколько новых новостей.

    Твоя задача:
    1. Определи, какие новости наиболее важные.
    2. Отсортируй их от самых важных к менее важным.
    3. Самые важные новости перескажи подробнее.
    4. Менее важные новости опиши очень кратко.
    5. Не пропускай значимые события.
    6. Не выдумывай факты.
    7. Используй только информацию из предоставленных текстов.

    Формат ответа:

    ГЛАВНОЕ

    1. Заголовок
    Коротко:
    Почему это важно:

    2. Заголовок
    Коротко:
    Почему это важно:

    ДЕТАЛИ

    - Дополнительные важные факты
    - Что ещё стоит знать

    МЕНЕЕ ВАЖНОЕ

    - Заголовок — одно предложение
    - Заголовок — одно предложение

    Новости:

    {combined_articles}
    """

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

        print("LLM status:", response.status_code)

        response.raise_for_status()

        data = response.json()

        message = data["choices"][0]["message"]

        digest = message.get("content", "").strip()

    except Exception as e:
        print("Ошибка Qwen:")
        print(e)

        digest = "Ошибка суммаризации."

    return digest
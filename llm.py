import requests
import json

LLM_URL = "http://127.0.0.1:8080/v1/chat/completions"


def summarize_article(article: list[dict], stream_callback=None) -> str:
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
    8. Выделяй названия разделов, заголовки новостей и подписи
       «Коротко:», «Почему это важно:» жирным Markdown: **текст**.
       Основной текст оставляй обычным. Не заключай ответ в блок кода.
    9. Заголовки пиши на русском языке

    Формат ответа:

    **ГЛАВНОЕ**

    1. **Заголовок**
    **Коротко:**
    **Почему это важно:**

    2. **Заголовок**
    **Коротко:**
    **Почему это важно:**

    **ДЕТАЛИ**

    - Дополнительные важные факты
    - Что ещё стоит знать

    **МЕНЕЕ ВАЖНОЕ**

    - Заголовок — одно предложение
    - Заголовок — одно предложение

    Новости:

    {combined_articles}
    """

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
            "max_tokens": 1800,
            "stream": True
        },
        stream=True,
        timeout=600
    )

    full_text = ""
    with response:
        response.raise_for_status()
        for line in response.iter_lines(chunk_size=1):
            if not line:
                continue
            decoded = line.decode("utf-8")
            if not decoded.startswith("data:"):
                continue
            data = decoded[5:].strip()
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            choices = chunk.get("choices") or []
            if not choices:
                continue
            content = choices[0].get("delta", {}).get("content")
            if content:
                if stream_callback is not None:
                    stream_callback(content)
                else:
                    print(content, end="", flush=True)
                full_text += content

    if stream_callback is None:
        print()

    return full_text

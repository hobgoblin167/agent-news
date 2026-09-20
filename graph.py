from typing import TypedDict
from typing import Callable

from langgraph.graph import StateGraph, START, END

from database import get_existing_ids, save_articles
from news import fetch_feed, fetch_article_text
from llm import summarize_article

#state наш
class NewState(TypedDict, total=False):
    feed_items:list[dict]
    new_articles:list[dict]
    digest:str
    log_callback: Callable
    stream_callback: Callable

def node_fetch_feed(state: NewState):

    log(
        state,
        "Получаем RSS..."
    )

    items = fetch_feed()

    log(
        state,
        f"Найдено статей: {len(items)}"
    )

    return {
        "feed_items": items
    }
def node_find_new(state: NewState):
    feed_items = state["feed_items"]
    ids=[
        article["id"]
        for article in feed_items]
    existing_ids = get_existing_ids(ids)
    new_articles = [
        article
        for article in feed_items
        if article["id"] not in existing_ids
    ]
    new_articles = new_articles
    return{
        "new_articles": new_articles
    }
#для логики роутер
def route_new_articles(state: NewState):
    if state.get("new_articles"):
        return "fetch_articles"

    return "end"

def node_fetch_article(state: NewState):
    articles = []

    for article in state["new_articles"]:
        log(
            state,
            f"Загрузка: {article['title']}"
        )

        article = fetch_article_text(
            article
        )

        articles.append(article)

    return {
        "new_articles": articles
    }
#суммаризация
def node_sum_article(state: NewState):
    articles = state["new_articles"]

    log(
        state,
        f"Отправляем {len(articles)} "
        f"новостей в Qwen..."
    )

    digest = summarize_article(articles, stream_callback=state.get("stream_callback"))

    return {
        "digest": digest
    }
def node_save(state: NewState):

    articles = state["new_articles"]

    save_articles(articles)

    print(f"Saved {len(articles)} articles")

    return {}

#logs
def log(state: NewState, text: str):

    callback = state.get(
        "log_callback"
    )

    if callback:

        callback(text)

    else:

        print(text)

#Строим граф
builder = StateGraph(NewState)
builder.add_node(
    "fetch_feed",
    node_fetch_feed
)
builder.add_node(
    "find_new",
    node_find_new
)
builder.add_node(
    "fetch_articles",
    node_fetch_article
)
builder.add_node(
    "summarize",
    node_sum_article
)
builder.add_node(
    "save",
    node_save
)
#последовательность
builder.add_edge(
    START,
    "fetch_feed"
)
builder.add_edge(
    "fetch_feed",
    "find_new"
)
builder.add_edge(
    "fetch_feed",
    "find_new"
)
builder.add_conditional_edges(
    "find_new",
    route_new_articles,
    {
        "fetch_articles": "fetch_articles",
        "end": END
    }
)
builder.add_edge(
    "fetch_articles",
    "summarize"
)
builder.add_edge(
    "summarize",
    "save"
)
builder.add_edge(
    "save",
    END
)
graph = builder.compile()

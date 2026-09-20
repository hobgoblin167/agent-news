from database import init_db, show_all_news
from graph import graph


def main():
    print("News Agent started")

    init_db()

    result = graph.invoke({})

    if result.get("digest"):
        print("\n")
        print("NEW NEWS")
        print(result["digest"])
    else:
        print("No new articles")


if __name__ == "__main__":
    main()
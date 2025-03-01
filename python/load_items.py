import json

def load_items():
    try:
        # items.jsonファイルを開いて読み込む
        with open("items.json", "r") as file:
            items = json.load(file)  # JSONを辞書型に変換して返す
            return items
    except FileNotFoundError:
        # items.jsonが見つからない場合、初期データを返す
        return {"items": []}

# テストとして呼び出してみる
items_data = load_items()
print(items_data)

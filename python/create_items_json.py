import json

# 初期データ
initial_data = {
    "items": []
}

# items.jsonファイルを作成し、初期データを格納
with open("items.json", "w") as file:
    json.dump(initial_data, file, indent=4)

print("items.json が作成されました")

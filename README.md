# Battle 2048

## Setup

```bash
python -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
cd src
LOGLEVEL=info python -m server.main
LOGLEVEL=info python -m client.main
```

## Protocol spec

```
server api: 透過 socket 或是 websocket 連線，資料一律以 json 格式處理，使用換行做為分隔
	client -> server:
		new_room(): server 回傳一個 id 當作 room id
		connect(room_id): 連線到對應的 room
		client_update(score, new_block): score 是目前分數，以及 client 端所合成的方塊資料 data
		client_win(score): 傳送勝利時的分數
	server -> client:
        new_room_id(): new_room 的回應
		connected(): server 通知兩端已經連接上了
		disconnected(): server 通知另一端已經離線了
		opponent_update(score, penalty_block): server 傳送來自另一端的更新資訊，包括對手分數，和懲罰的方塊
		opponent_win(score): 對手勝利了，包含對手的分數
```
